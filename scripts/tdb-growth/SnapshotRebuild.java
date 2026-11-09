/** Rebuild a stopped disposable snapshot into NEW /rebuilt/dataset for storage comparison.
 * Never bind live storage or backup originals. Copies all quads including internal
 * receipts, verifies every source quad and equal target count, and preserves source
 * RDF data. This is not a complete application restore: fulltext/configuration are
 * deliberately excluded. Mounts need exclusive ownership and network isolation.
 */
import org.apache.jena.query.*;
import org.apache.jena.tdb2.TDB2Factory;
import java.nio.file.*;
public class SnapshotRebuild {
 public static void main(String[] args) throws Exception {
  // Fixed disposable mounts: never accepts a live database path or overwrites a target.
  Path target=Path.of("/rebuilt/dataset"); Files.createDirectory(target);
  Dataset source=TDB2Factory.connectDataset("/snapshot");
  Dataset dest=TDB2Factory.connectDataset(target.toString());
  try {
   source.begin(ReadWrite.READ); dest.begin(ReadWrite.WRITE);
   long count=0;
   try {
    var quads=source.asDatasetGraph().find();
    while(quads.hasNext()) {dest.asDatasetGraph().add(quads.next());count++;}
    dest.commit();
   } finally {dest.end();source.end();}
   source.begin(ReadWrite.READ);dest.begin(ReadWrite.READ);
   try {
    long verified=0;var quads=source.asDatasetGraph().find();
    while(quads.hasNext()) {if(!dest.asDatasetGraph().contains(quads.next()))throw new IllegalStateException("Missing quad");verified++;}
    long actual=0;var copied=dest.asDatasetGraph().find();while(copied.hasNext()){copied.next();actual++;}
    if(actual!=verified || actual!=count)throw new IllegalStateException("Count mismatch");
    System.out.println("{\"verified_quads\":"+actual+"}");
   } finally {dest.end();source.end();}
  } finally {dest.close();source.close();}
 }
}
