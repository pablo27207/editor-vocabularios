from flask import Blueprint, request, Response, abort
from models import Vocabulary
from utils.export import generate_rdf_graph, export_to_csv
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
        
    if format == 'rdf': # XML
        data = g.serialize(format='xml')
        mimetype = "application/rdf+xml"
    elif format == 'ttl': # Turtle
        data = g.serialize(format='turtle')
        mimetype = "text/turtle"
    else:
        abort(400)
        
    return Response(
        data,
        mimetype=mimetype,
        headers={"Content-disposition": f"attachment; filename=vocab_{vocab_id}.{format}"}
    )

@sparql_bp.route('/sparql', methods=['GET', 'POST'])
def sparql_endpoint():
    # This is a simplified SPARQL endpoint that queries ALL vocabularies.
    # In a real production system with massive data, you'd use a dedicated Triple Store (Virtuoso/Fuseki).
    # Here we construct the graph on the fly or cache it. For this scale, on-the-fly might be slow but functional.
    # Optimization: Cache the graph globally and invalidate on updates.
    
    query = request.args.get('query') or request.form.get('query')
    if not query:
        return "No query provided", 400
        
    # Aggregate all vocabs into one graph (or just the requested one if we had named graphs)
    full_graph = rdflib.Graph()
    vocabularies = Vocabulary.query.all()
    for vocab in vocabularies:
        g = generate_rdf_graph(vocab.id)
        if g:
            full_graph += g
            
    try:
        results = full_graph.query(query)
        # Return JSON results
        return Response(results.serialize(format='json'), mimetype='application/sparql-results+json')
    except Exception as e:
        return str(e), 400
