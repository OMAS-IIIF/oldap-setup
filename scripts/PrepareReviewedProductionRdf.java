import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;
import java.util.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.update.UpdateAction;

/** Apply only the two explicitly approved data corrections to a private RDF copy.
 * No database/network access. Require the exact converted input hash, one known
 * recovery-default removal, zero part-preflight findings and exact quad-set
 * preservation outside canonical part reversal. Publish a new private output.
 */
public final class PrepareReviewedProductionRdf {
    static Set<Quad> snapshot(Dataset data) {
        Set<Quad> result = new HashSet<>();
        data.asDatasetGraph().find().forEachRemaining(result::add);
        return result;
    }
    static String hash(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 6) throw new IllegalArgumentException("Expected input SHA recovery.ru parts-preflight.rq parts.ru NEW-output");
        Path output = Path.of(args[5]);
        if (Files.exists(output)) throw new IllegalArgumentException("Output must be new");
        byte[] source = Files.readAllBytes(Path.of(args[0]));
        if (!hash(source).equals(args[1])) throw new IllegalArgumentException("Converted source checksum differs");
        Dataset data = DatasetFactory.createTxnMem();
        try {
            data.begin(ReadWrite.WRITE);
            RDFParser.fromString(new String(source, java.nio.charset.StandardCharsets.UTF_8), Lang.TRIG).checking(true).parse(data);
            Set<Quad> before = snapshot(data);
            UpdateAction.parseExecute(Files.readString(Path.of(args[2])), data);
            Set<Quad> afterDefault = snapshot(data);
            Set<Quad> removed = new HashSet<>(before); removed.removeAll(afterDefault);
            Set<Quad> added = new HashSet<>(afterDefault); added.removeAll(before);
            if (removed.size()!=1 || !added.isEmpty()) throw new IllegalStateException("Expected exactly the approved single default correction");
            Quad change = removed.iterator().next();
            if (!change.getGraph().equals(NodeFactory.createURI("http://oldap.org/base#admin")) ||
                !change.getPredicate().equals(NodeFactory.createURI("http://oldap.org/base#hasDefaultDataPermission")) ||
                !change.getObject().equals(NodeFactory.createURI("http://oldap.org/base#DATA_VIEW")))
                throw new IllegalStateException("Unexpected default correction");
            try (QueryExecution query=QueryExecutionFactory.create(Files.readString(Path.of(args[3])),data)) {
                if (query.execSelect().hasNext()) throw new IllegalStateException("Part relationship preflight has findings");
            }
            var graph=NodeFactory.createURI("http://fasnacht.digital/ns/data");
            var has=NodeFactory.createURI("http://purl.org/dc/terms/hasPart");
            var part=NodeFactory.createURI("http://purl.org/dc/terms/isPartOf");
            Set<Quad> expected=new HashSet<>(afterDefault);
            int reversed=0;
            for (Quad q:afterDefault) if (q.getGraph().equals(graph) && q.getPredicate().equals(has)) {
                expected.remove(q); expected.add(Quad.create(graph,q.getObject(),part,q.getSubject())); reversed++;
            }
            UpdateAction.parseExecute(Files.readString(Path.of(args[4])),data);
            if (!snapshot(data).equals(expected)) throw new IllegalStateException("Part reversal changed other RDF");
            data.commit(); data.end();
            data.begin(ReadWrite.READ);
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();
            RDFDataMgr.write(bytes,data,RDFFormat.TRIG_PRETTY);
            Dataset roundtrip=DatasetFactory.create();
            try {
                RDFParser.fromString(bytes.toString(java.nio.charset.StandardCharsets.UTF_8),Lang.TRIG).checking(true).parse(roundtrip);
                if (!ConvertLegacyRdfStar.sameDataset(data,roundtrip)) throw new IllegalStateException("Corrected RDF round-trip differs");
            } finally {roundtrip.close();}
            Files.createDirectory(output,PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
            Files.write(output.resolve("reviewed.trig"),bytes.toByteArray(),StandardOpenOption.CREATE_NEW);
            String report="{\"status\":\"passed\",\"inputSha256\":\""+args[1]+"\",\"outputSha256\":\""+hash(bytes.toByteArray())+"\",\"defaultPermissionsRemoved\":1,\"hasPartReversed\":"+reversed+",\"otherQuadsUnchanged\":true,\"roundTripVerified\":true}\n";
            Files.writeString(output.resolve("report.json"),report,StandardOpenOption.CREATE_NEW);
            data.end();
            System.out.println("Reviewed RDF corrections verified; source and databases unchanged.");
        } finally {
            if (data.isInTransaction()) {data.abort();data.end();}
            data.close();
        }
    }
}
