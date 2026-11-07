import java.nio.file.*;
import java.util.*;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;

/** Isolated storage experiment using the exact deployed OLDAP service jar.
 * Creates a NEW dataset only. Compares ordinary reads, empty committed sessions,
 * and empty aborted sessions over identical synthetic domain data. No HTTP,
 * credentials, fulltext, production data or compaction are involved.
 * Compile with javac against both jars first, then run the compiled class in
 * the same classloader as the service (package-private diagnostic access).
 * Usage: java -cp 'classes:service.jar:fuseki-server.jar' TdbIdleGrowthProbe NEW_ROOT MODE ROUNDS
 */
public class TdbIdleGrowthProbe {
    static void sample(JenaSessionEngine engine, Path root, String mode, int rounds) throws Exception {
        long logical;
        try (var paths = Files.walk(root)) {
            logical = paths.filter(Files::isRegularFile).mapToLong(p -> {
                try { return Files.size(p); } catch (Exception e) { throw new RuntimeException(e); }
            }).sum();
        }
        engine.storage.begin(ReadWrite.READ);
        try {
            long receipts = engine.storage.getNamedModel(JenaSessionEngine.RECEIPTS).size();
            long domain = engine.storage.getNamedModel("urn:growth:domain").size();
            System.out.printf(Locale.ROOT,
                "{\"mode\":\"%s\",\"rounds\":%d,\"logical_bytes\":%d,\"receipt_triples\":%d,\"domain_triples\":%d}%n",
                mode, rounds, logical, receipts, domain);
        } finally { engine.storage.end(); }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("NEW_ROOT read|commit|abort ROUNDS");
        Path root = Path.of(args[0]).toAbsolutePath();
        String mode = args[1];
        int rounds = Integer.parseInt(args[2]);
        if (!Set.of("read", "commit", "abort").contains(mode) || rounds < 1 || rounds > 10000)
            throw new IllegalArgumentException("Invalid mode/round count");
        Files.createDirectory(root); // Refuse existing datasets, including symlinks.
        try (JenaSessionEngine engine = new JenaSessionEngine(root.toString(), 60000)) {
            engine.storage.begin(ReadWrite.WRITE);
            try {
                Model model = engine.storage.getNamedModel("urn:growth:domain");
                for (int i = 0; i < 10000; i++)
                    model.add(model.createResource("urn:growth:item:" + i),
                        model.createProperty("urn:growth:label"), "Item " + i);
                engine.storage.commit();
            } finally { engine.storage.end(); }
            sample(engine, root, mode, 0);
            for (int i = 1; i <= rounds; i++) {
                UUID id = UUID.randomUUID();
                String query = "ASK { GRAPH <urn:growth:jobs> { ?s ?p ?o } }";
                if (mode.equals("read")) engine.dispatch("READ", id, "growth-probe", query);
                else {
                    engine.dispatch("BEGIN", id, "growth-probe", "");
                    engine.dispatch("QUERY", id, "growth-probe", query);
                    engine.dispatch(mode.equals("commit") ? "COMMIT" : "ABORT", id, "growth-probe", "");
                }
                if (i % 250 == 0 || i == rounds) sample(engine, root, mode, i);
            }
        }
    }
}
