import java.util.*;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.sparql.core.Quad;

/** Offline safety checks: approved cleanup must not erase shared/unreviewed RDF. */
public final class ProductionModelCleanupChecks {
    static Set<Quad> fixture() {
        Set<Quad> data = new HashSet<>();
        for (String name : List.of("Place", "CarnivalThing")) {
            var shape = NodeFactory.createBlankNode(name);
            data.add(Quad.create(PrepareProductionModel.SHACL, PrepareProductionModel.iri(PrepareProductionModel.NS+name+"Shape"), PrepareProductionModel.PROPERTY, shape));
            data.add(Quad.create(PrepareProductionModel.SHACL, shape, PrepareProductionModel.PATH, PrepareProductionModel.HAS));
        }
        data.add(Quad.create(PrepareProductionModel.ONTO, PrepareProductionModel.HAS, PrepareProductionModel.INVERSE, PrepareProductionModel.PART));
        return data;
    }
    static void rejects(Set<Quad> data) {
        try { PrepareProductionModel.removals(data); }
        catch (IllegalStateException expected) { return; }
        throw new AssertionError("Unsafe input was accepted");
    }
    public static void main(String[] args) {
        var data=fixture();
        var unrelated=Quad.create(PrepareProductionModel.iri("urn:other:onto"), PrepareProductionModel.HAS, PrepareProductionModel.INVERSE, PrepareProductionModel.PART);
        data.add(unrelated);
        var removed=PrepareProductionModel.removals(data);
        if(removed.size()!=5 || removed.contains(unrelated)) throw new AssertionError("Wrong scope");
        data.removeAll(removed);
        if(!PrepareProductionModel.removals(data).isEmpty()) throw new AssertionError("Not idempotent");
        data=fixture();data.add(Quad.create(PrepareProductionModel.DATA, PrepareProductionModel.iri("urn:parent"), PrepareProductionModel.HAS, PrepareProductionModel.iri("urn:child")));rejects(data);
        data=fixture();data.add(Quad.create(PrepareProductionModel.SHACL, PrepareProductionModel.iri("urn:other:owner"), PrepareProductionModel.PROPERTY, NodeFactory.createBlankNode("Place")));rejects(data);
        data=fixture();data.add(Quad.create(PrepareProductionModel.ONTO, PrepareProductionModel.iri("urn:restriction"), PrepareProductionModel.iri("http://www.w3.org/2002/07/owl#onProperty"), PrepareProductionModel.HAS));rejects(data);
        data=fixture();data.removeIf(q->q.getSubject().equals(PrepareProductionModel.iri(PrepareProductionModel.NS+"PlaceShape")));rejects(data);
        data=fixture();data.add(Quad.create(PrepareProductionModel.SHACL, NodeFactory.createBlankNode("Place"), PrepareProductionModel.iri("urn:nested"), NodeFactory.createBlankNode()));rejects(data);
        data=fixture();data.add(Quad.create(PrepareProductionModel.ONTO, PrepareProductionModel.iri("urn:annotation"), PrepareProductionModel.iri("http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies"), NodeFactory.createTripleTerm(Triple.create(PrepareProductionModel.HAS, PrepareProductionModel.INVERSE, PrepareProductionModel.PART))));rejects(data);
        System.out.println("Seven model cleanup safety checks passed");
    }
}
