"""Export service - Generate RDF graphs and CSV exports."""
from rdflib import Graph, Namespace, RDF, SKOS, URIRef, Literal
from app.models import Vocabulary, Term
import csv
import io


def generate_rdf_graph(vocab_id):
    """Generate an RDF graph for a vocabulary."""
    vocab = Vocabulary.query.get(vocab_id)
    if not vocab:
        return None
        
    g = Graph()
    base_uri = vocab.base_uri or f"http://example.org/vocab/{vocab.code}/"
    if not base_uri.endswith('/'):
        base_uri += '/'
    
    NS = Namespace(base_uri)
    g.bind('skos', SKOS)
    g.bind('vocab', NS)
    
    # Scheme
    scheme_uri = URIRef(base_uri)
    g.add((scheme_uri, RDF.type, SKOS.ConceptScheme))
    g.add((scheme_uri, SKOS.prefLabel, Literal(vocab.name, lang='es')))
    if vocab.description:
        g.add((scheme_uri, SKOS.definition, Literal(vocab.description, lang='es')))
        
    # Terms
    terms = Term.query.filter_by(vocab_id=vocab_id, status='approved').all()
    for term in terms:
        term_uri = URIRef(base_uri + term.concept_id)
        g.add((term_uri, RDF.type, SKOS.Concept))
        g.add((term_uri, SKOS.inScheme, scheme_uri))
        
        if term.pref_label_es:
            g.add((term_uri, SKOS.prefLabel, Literal(term.pref_label_es, lang='es')))
        if term.pref_label_en:
            g.add((term_uri, SKOS.prefLabel, Literal(term.pref_label_en, lang='en')))
            
        if term.definition_es:
            g.add((term_uri, SKOS.definition, Literal(term.definition_es, lang='es')))
        if term.definition_en:
            g.add((term_uri, SKOS.definition, Literal(term.definition_en, lang='en')))
            
        # Relationships
        if term.broader:
            for broader_id in term.broader:
                g.add((term_uri, SKOS.broader, URIRef(base_uri + broader_id)))
                
        if term.narrower:
            for narrower_id in term.narrower:
                g.add((term_uri, SKOS.narrower, URIRef(base_uri + narrower_id)))

    return g


def export_to_csv(vocab_id):
    """Export vocabulary terms to CSV format."""
    vocab = Vocabulary.query.get(vocab_id)
    terms = Term.query.filter_by(vocab_id=vocab_id, status='approved').all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'PrefLabel (ES)', 'PrefLabel (EN)', 'Definition (ES)', 'Definition (EN)', 'Broader'])
    
    for term in terms:
        broader_str = ','.join(term.broader) if term.broader else ''
        writer.writerow([
            term.concept_id,
            term.pref_label_es,
            term.pref_label_en,
            term.definition_es,
            term.definition_en,
            broader_str
        ])
        
    return output.getvalue()
