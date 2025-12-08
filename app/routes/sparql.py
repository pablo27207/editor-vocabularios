"""SPARQL and export routes."""
from flask import Blueprint, request, Response, abort
from app.models import Vocabulary
from app.services.export import generate_rdf_graph, export_to_csv
import rdflib

sparql_bp = Blueprint('sparql', __name__)


@sparql_bp.route('/vocab/<int:vocab_id>/export/<format>')
def export_vocab(vocab_id, format):
    if format == 'csv':
        csv_data = export_to_csv(vocab_id)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=vocab_{vocab_id}.csv"}
        )
    
    # RDF formats
    g = generate_rdf_graph(vocab_id)
    if not g:
        abort(404)
        
    if format == 'rdf':  # XML
        data = g.serialize(format='xml')
        mimetype = "application/rdf+xml"
    elif format == 'ttl':  # Turtle
        data = g.serialize(format='turtle')
        mimetype = "text/turtle"
    elif format == 'jsonld':  # JSON-LD
        data = g.serialize(format='json-ld')
        mimetype = "application/ld+json"
    else:
        abort(400)
        
    return Response(
        data,
        mimetype=mimetype,
        headers={"Content-disposition": f"attachment; filename=vocab_{vocab_id}.{format}"}
    )


@sparql_bp.route('/sparql', methods=['GET', 'POST'])
def sparql_endpoint():
    """Simplified SPARQL endpoint that queries ALL vocabularies."""
    query = request.args.get('query') or request.form.get('query')
    if not query:
        return "No query provided", 400
        
    # Aggregate all vocabs into one graph
    full_graph = rdflib.Graph()
    vocabularies = Vocabulary.query.all()
    for vocab in vocabularies:
        g = generate_rdf_graph(vocab.id)
        if g:
            full_graph += g
            
    try:
        results = full_graph.query(query)
        return Response(results.serialize(format='json'), mimetype='application/sparql-results+json')
    except Exception as e:
        return str(e), 400
