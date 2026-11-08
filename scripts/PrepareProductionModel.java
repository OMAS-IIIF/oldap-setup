import java.io.ByteArrayOutputStream;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.*;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
import org.apache.jena.sparql.core.Quad;

/** Remove only the approved obsolete Fasnacht hasPart model from an offline copy.
 * Instance reversal must already have run. Unexpected owners, shared blank nodes,
 * nested shape structure or additional hasPart model references stop the migration.
 * Other projects, external vocabularies and all instance/administrative RDF stay
 * byte-term equivalent. No live store, network or ordinary model-delete API is used.
 */
public final class PrepareProductionModel {
    static final String NS = "http://fasnacht.digital/ns/";
    static final Node SHACL = iri(NS + "shacl"), ONTO = iri(NS + "onto");
    static final Node DATA = iri(NS + "data"), HAS = iri("http://purl.org/dc/terms/hasPart");
    static final Node PART = iri("http://purl.org/dc/terms/isPartOf");
    static final Node PATH = iri("http://www.w3.org/ns/shacl#path");
    static final Node PROPERTY = iri("http://www.w3.org/ns/shacl#property");
    static final Node INVERSE = iri("http://www.w3.org/2002/07/owl#inverseOf");
    static final Node TYPE = iri("http://www.w3.org/1999/02/22-rdf-syntax-ns#type");
    static final Node OBJECT_PROPERTY = iri("http://www.w3.org/2002/07/owl#ObjectProperty");
    static Node iri(String value) { return NodeFactory.createURI(value); }

    /** Detect RDF 1.2 annotations referring to a shape before deleting that shape. */
    static boolean references(Node value, Node shape) {
        if (value.equals(shape)) return true;
        if (!value.isTripleTerm()) return false;
        var triple = value.getTriple();
        return references(triple.getSubject(), shape) || references(triple.getPredicate(), shape)
            || references(triple.getObject(), shape);
    }

    /** Snapshot exact terms, retaining blank-node identity inside this dataset. */
    static Set<Quad> snapshot(Dataset data) {
        Set<Quad> result = new HashSet<>();
        data.asDatasetGraph().find().forEachRemaining(result::add);
        return result;
    }

    /** Compute the complete approved deletion set before applying any mutation.
     * The caller owns the transaction. Repeated use on the cleaned model is a no-op.
     */
    static Set<Quad> removals(Set<Quad> before) {
        Set<Quad> removed = new HashSet<>();
        Set<Node> shapes = new HashSet<>(), owners = new HashSet<>();
        Set<Node> expectedOwners = Set.of(iri(NS + "PlaceShape"), iri(NS + "CarnivalThingShape"));
        for (Quad q : before) {
            if ((q.getGraph().equals(ONTO) || q.getGraph().equals(SHACL)) &&
                ((q.getSubject().isTripleTerm() && references(q.getSubject(), HAS)) ||
                 (q.getObject().isTripleTerm() && references(q.getObject(), HAS))))
                throw new IllegalStateException("Annotated hasPart model requires explicit review");
            if (q.getGraph().equals(DATA) && q.getPredicate().equals(HAS))
                throw new IllegalStateException("Reverse instance hasPart assertions before model cleanup");
            if (q.getGraph().equals(SHACL) && q.getPredicate().equals(PATH) && q.getObject().equals(HAS))
                shapes.add(q.getSubject());
        }
        for (Node shape : shapes) {
            if (!shape.isBlank()) throw new IllegalStateException("Expected private inline property shape");
            int links = 0;
            for (Quad q : before) {
                if ((q.getSubject().isTripleTerm() && references(q.getSubject(), shape)) ||
                    (q.getObject().isTripleTerm() && references(q.getObject(), shape)))
                    throw new IllegalStateException("Annotated model requires explicit review");
                if (q.getSubject().equals(shape)) {
                    if (!q.getGraph().equals(SHACL) || (!q.getObject().isLiteral() && !q.getObject().isURI()))
                        throw new IllegalStateException("Unexpected nested or cross-graph shape structure");
                    removed.add(q);
                }
                if (q.getObject().equals(shape)) {
                    if (!q.getGraph().equals(SHACL) || !q.getPredicate().equals(PROPERTY) || !expectedOwners.contains(q.getSubject()))
                        throw new IllegalStateException("Property shape is shared or has an unexpected owner");
                    owners.add(q.getSubject()); links++; removed.add(q);
                }
                if (q.getGraph().equals(shape)) throw new IllegalStateException("Shape used as graph name");
            }
            if (links != 1) throw new IllegalStateException("Expected one owner per obsolete property shape");
        }
        if (!shapes.isEmpty() && (shapes.size() != 2 || !owners.equals(expectedOwners)))
            throw new IllegalStateException("Expected both approved obsolete fields, or neither on replay");
        Set<Quad> axioms = Set.of(
            Quad.create(ONTO, HAS, INVERSE, PART), Quad.create(ONTO, PART, INVERSE, HAS),
            Quad.create(ONTO, HAS, TYPE, OBJECT_PROPERTY));
        for (Quad q : before) {
            if (axioms.contains(q)) removed.add(q);
            if ((q.getGraph().equals(ONTO) || q.getGraph().equals(SHACL)) &&
                (q.getSubject().equals(HAS) || q.getPredicate().equals(HAS) || q.getObject().equals(HAS)) && !removed.contains(q))
                throw new IllegalStateException("Unreviewed hasPart model reference");
        }
        return removed;
    }

    static String hash(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    /** Require input hash and a fresh output directory; verify lossless serialization. */
    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("Expected input.trig SHA256 NEW-output-directory");
        byte[] input = Files.readAllBytes(Path.of(args[0]));
        if (!hash(input).equals(args[1])) throw new IllegalArgumentException("Input checksum mismatch");
        Path output = Path.of(args[2]);
        if (Files.exists(output)) throw new IllegalArgumentException("Output must be new");
        Dataset data = DatasetFactory.createTxnMem();
        try {
            data.begin(ReadWrite.WRITE);
            RDFParser.fromString(new String(input, java.nio.charset.StandardCharsets.UTF_8), Lang.TRIG).checking(true).parse(data);
            Set<Quad> before = snapshot(data), removed = removals(before);
            removed.forEach(data.asDatasetGraph()::delete);
            Set<Quad> expected = new HashSet<>(before); expected.removeAll(removed);
            if (!snapshot(data).equals(expected) || !removals(snapshot(data)).isEmpty())
                throw new IllegalStateException("Unexpected changes or non-idempotent cleanup");
            data.commit(); data.end(); data.begin(ReadWrite.READ);
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            RDFDataMgr.write(bytes, data, RDFFormat.TRIG_PRETTY);
            Dataset parsed = DatasetFactory.create();
            try {
                RDFParser.fromString(bytes.toString(java.nio.charset.StandardCharsets.UTF_8), Lang.TRIG).checking(true).parse(parsed);
                if (!ConvertLegacyRdfStar.sameDataset(data, parsed)) throw new IllegalStateException("Round-trip changed RDF");
            } finally { parsed.close(); }
            Files.createDirectory(output, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
            Files.write(output.resolve("model-reviewed.trig"), bytes.toByteArray(), StandardOpenOption.CREATE_NEW);
            String report = "{\"status\":\"passed\",\"inputSha256\":\""+args[1]+"\",\"outputSha256\":\""+hash(bytes.toByteArray())+
                "\",\"removedModelQuads\":"+removed.size()+",\"beforeQuads\":"+before.size()+",\"afterQuads\":"+expected.size()+
                ",\"allOtherQuadsUnchanged\":true,\"idempotent\":true,\"roundTripVerified\":true}\n";
            Files.writeString(output.resolve("report.json"), report, StandardOpenOption.CREATE_NEW);
            data.end();
            System.out.println(report);
        } finally {
            if (data.isInTransaction()) { data.abort(); data.end(); }
            data.close();
        }
    }
}
