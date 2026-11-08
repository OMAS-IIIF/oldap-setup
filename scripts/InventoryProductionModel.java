import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.*;
import org.apache.jena.atlas.json.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;

/** Read a checksum-bound offline RDF snapshot and inventory projects/model links.
 * Fixed SELECT queries return metadata only, never account records or passwords.
 * The projects.json output is consumed by check-production-fulltext.py. GraphDB
 * connector configuration must separately come from the paired filesystem backup.
 */
public final class InventoryProductionModel {
    public static void main(String[] args) throws Exception {
        if (args.length!=3) throw new IllegalArgumentException("Expected input.trig SHA256 NEW-output-directory");
        byte[] bytes=Files.readAllBytes(Path.of(args[0]));
        String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        if(!hash.equals(args[1])) throw new IllegalArgumentException("Snapshot checksum mismatch");
        Path output=Path.of(args[2]);
        if(Files.exists(output)) throw new IllegalArgumentException("Output must be new");
        Map<String,String> queries=new TreeMap<>();
        queries.put("projects", "PREFIX oldap:<http://oldap.org/base#> SELECT ?project ?name ?namespace WHERE {GRAPH oldap:admin {?project a oldap:Project; oldap:projectShortName ?name; oldap:namespaceIri ?namespace}} ORDER BY ?name");
        queries.put("graphs", "SELECT ?graph (COUNT(*) AS ?count) WHERE {GRAPH ?graph {?s ?p ?o}} GROUP BY ?graph ORDER BY ?graph");
        queries.put("relations", "PREFIX owl:<http://www.w3.org/2002/07/owl#> SELECT ?graph ?subject ?predicate ?object WHERE {GRAPH ?graph {?subject ?predicate ?object} VALUES ?predicate {owl:inverseOf owl:equivalentClass owl:equivalentProperty}} ORDER BY ?graph ?subject ?predicate ?object");
        Dataset data=DatasetFactory.create();
        try {
            RDFParser.fromString(new String(bytes,java.nio.charset.StandardCharsets.UTF_8),Lang.TRIG).checking(true).parse(data);
            Files.createDirectory(output,PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
            for(var entry:queries.entrySet()) {
                JsonArray rows=new JsonArray();
                try(QueryExecution query=QueryExecutionFactory.create(entry.getValue(),data)) {
                    ResultSet result=query.execSelect();
                    while(result.hasNext()) {
                        var solution=result.next(); JsonObject row=new JsonObject();
                        for(String key:result.getResultVars()) {
                            var value=solution.get(key);
                            row.put(key,value.isLiteral()?value.asLiteral().getString():value.asResource().getURI());
                        }
                        rows.add(row);
                    }
                }
                Files.writeString(output.resolve(entry.getKey()+".json"),JSON.toString(rows)+"\n",StandardOpenOption.CREATE_NEW);
            }
            Files.writeString(output.resolve("source.sha256"),hash+"\n",StandardOpenOption.CREATE_NEW);
        } finally {data.close();}
    }
}
