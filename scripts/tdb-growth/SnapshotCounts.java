/** Count named-graph triples in an exclusively opened, stopped disposable snapshot.
 * Fixed /snapshot mount; never bind live storage. Opens READ transactions only.
 * TDB still needs a writable mount for locks/recovery; do not use backup originals.
 */
import org.apache.jena.query.*;
import org.apache.jena.tdb2.TDB2Factory;
public class SnapshotCounts {
 public static void main(String[] args) {
  Dataset d=TDB2Factory.connectDataset("/snapshot");
  try {
   d.begin(ReadWrite.READ);
   try (QueryExecution q=QueryExecutionFactory.create("SELECT ?g (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g",d)) {
    org.apache.jena.query.ResultSetFormatter.outputAsJSON(System.out,q.execSelect());
   } finally {d.end();}
  } finally {d.close();}
 }
}
