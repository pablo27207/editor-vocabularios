"""Import service for vocabulary files (RDF/XML, Turtle, JSON-LD)."""
from rdflib import Graph, Namespace, RDF, SKOS, DCTERMS, RDFS
from app.models import db, Vocabulary, Term


def parse_rdf_file(file_content, format):
    """
    Parse RDF file content and return an rdflib Graph.
    
    Args:
        file_content: File content as bytes or string
        format: 'xml' for RDF/XML, 'turtle' for Turtle, 'json-ld' for JSON-LD
    
    Returns:
        rdflib.Graph or None if parsing fails
    """
    g = Graph()
    try:
        g.parse(data=file_content, format=format)
        return g
    except Exception as e:
        print(f"Error parsing RDF: {e}")
        return None


def extract_vocabulary_info(graph):
    """
    Extract vocabulary metadata from RDF graph.
    
    Returns dict with code, name, description, etc.
    """
    # Find ConceptScheme
    scheme = None
    for s in graph.subjects(RDF.type, SKOS.ConceptScheme):
        scheme = s
        break
    
    if not scheme:
        # Try to infer from concepts
        for s in graph.subjects(RDF.type, SKOS.Concept):
            # Use the namespace as scheme
            scheme_uri = str(s).rsplit('/', 1)[0] + '/'
            return {
                'uri': scheme_uri,
                'code': scheme_uri.split('/')[-2] if '/' in scheme_uri else 'imported',
                'name': 'Imported Vocabulary',
                'name_en': None,
                'description': None,
                'description_en': None
            }
    
    # Extract metadata from scheme
    info = {
        'uri': str(scheme),
        'code': str(scheme).split('/')[-1] or str(scheme).split('/')[-2],
        'name': None,
        'name_en': None,
        'description': None,
        'description_en': None
    }
    
    # Get labels
    for label in graph.objects(scheme, SKOS.prefLabel):
        lang = label.language
        if lang == 'es':
            info['name'] = str(label)
        elif lang == 'en':
            info['name_en'] = str(label)
        elif not info['name']:
            info['name'] = str(label)
    
    # Try dcterms:title if no prefLabel
    if not info['name']:
        for title in graph.objects(scheme, DCTERMS.title):
            info['name'] = str(title)
            break
    
    # Get descriptions
    for desc in graph.objects(scheme, SKOS.definition):
        lang = desc.language if hasattr(desc, 'language') else None
        if lang == 'es':
            info['description'] = str(desc)
        elif lang == 'en':
            info['description_en'] = str(desc)
        elif not info['description']:
            info['description'] = str(desc)
    
    # Try dcterms:description
    if not info['description']:
        for desc in graph.objects(scheme, DCTERMS.description):
            info['description'] = str(desc)
            break
    
    return info


def extract_terms(graph):
    """
    Extract all SKOS concepts from graph.
    
    Returns list of term dicts.
    """
    terms = []
    
    for concept in graph.subjects(RDF.type, SKOS.Concept):
        term = {
            'concept_id': str(concept).split('/')[-1] or str(concept).split('#')[-1],
            'uri': str(concept),
            'pref_label_es': None,
            'pref_label_en': None,
            'definition_es': None,
            'definition_en': None,
            'alt_labels': [],
            'broader': [],
            'narrower': [],
            'related': [],
            'exact_match': [],
            'close_match': [],
            'source': None
        }
        
        # Preferred labels
        for label in graph.objects(concept, SKOS.prefLabel):
            lang = label.language if hasattr(label, 'language') else None
            if lang == 'es':
                term['pref_label_es'] = str(label)
            elif lang == 'en':
                term['pref_label_en'] = str(label)
            elif not term['pref_label_es']:
                term['pref_label_es'] = str(label)
        
        # Alt labels
        for label in graph.objects(concept, SKOS.altLabel):
            term['alt_labels'].append(str(label))
        
        # Definitions
        for defn in graph.objects(concept, SKOS.definition):
            lang = defn.language if hasattr(defn, 'language') else None
            if lang == 'es':
                term['definition_es'] = str(defn)
            elif lang == 'en':
                term['definition_en'] = str(defn)
            elif not term['definition_es']:
                term['definition_es'] = str(defn)
        
        # Hierarchical relations
        for broader in graph.objects(concept, SKOS.broader):
            term['broader'].append(str(broader).split('/')[-1] or str(broader).split('#')[-1])
        
        for narrower in graph.objects(concept, SKOS.narrower):
            term['narrower'].append(str(narrower).split('/')[-1] or str(narrower).split('#')[-1])
        
        for related in graph.objects(concept, SKOS.related):
            term['related'].append(str(related).split('/')[-1] or str(related).split('#')[-1])
        
        # Mappings
        for match in graph.objects(concept, SKOS.exactMatch):
            term['exact_match'].append(str(match))
        
        for match in graph.objects(concept, SKOS.closeMatch):
            term['close_match'].append(str(match))
        
        # Source
        for source in graph.objects(concept, DCTERMS.source):
            term['source'] = str(source)
            break
        
        terms.append(term)
    
    return terms


def create_vocabulary_from_graph(graph, override_info=None):
    """
    Create a new Vocabulary and its Terms from parsed RDF graph.
    
    Args:
        graph: rdflib.Graph with vocabulary data
        override_info: Optional dict to override extracted metadata
    
    Returns:
        Vocabulary object or None on error
    """
    vocab_info = extract_vocabulary_info(graph)
    
    # Apply overrides
    if override_info:
        for key, value in override_info.items():
            if value:
                vocab_info[key] = value
    
    # Ensure we have a name
    if not vocab_info.get('name'):
        vocab_info['name'] = 'Imported Vocabulary'
    
    # Create vocabulary
    vocab = Vocabulary(
        code=vocab_info.get('code', 'imported'),
        name=vocab_info['name'],
        name_en=vocab_info.get('name_en'),
        description=vocab_info.get('description'),
        description_en=vocab_info.get('description_en'),
        base_uri=vocab_info.get('uri')
    )
    
    db.session.add(vocab)
    db.session.flush()  # Get vocab.id
    
    # Extract and create terms
    terms_data = extract_terms(graph)
    for term_data in terms_data:
        term = Term(
            vocab_id=vocab.id,
            concept_id=term_data['concept_id'],
            pref_label_es=term_data['pref_label_es'],
            pref_label_en=term_data['pref_label_en'],
            definition_es=term_data['definition_es'],
            definition_en=term_data['definition_en'],
            alt_labels=term_data['alt_labels'] if term_data['alt_labels'] else None,
            broader=term_data['broader'] if term_data['broader'] else None,
            narrower=term_data['narrower'] if term_data['narrower'] else None,
            related=term_data['related'] if term_data['related'] else None,
            exact_match=term_data['exact_match'] if term_data['exact_match'] else None,
            close_match=term_data['close_match'] if term_data['close_match'] else None,
            source=term_data['source']
        )
        db.session.add(term)
    
    db.session.commit()
    return vocab


def update_vocabulary_from_graph(vocab_id, graph, add_new=True, update_existing=True):
    """
    Update an existing Vocabulary with terms from parsed RDF graph.
    
    Args:
        vocab_id: ID of vocabulary to update
        graph: rdflib.Graph with vocabulary data
        add_new: Whether to add new concepts not in the vocabulary
        update_existing: Whether to update existing concepts
    
    Returns:
        dict with stats: {'added': int, 'updated': int, 'skipped': int}
    """
    vocab = Vocabulary.query.get(vocab_id)
    if not vocab:
        return None
    
    # Get existing terms by concept_id
    existing_terms = {t.concept_id: t for t in Term.query.filter_by(vocab_id=vocab_id).all()}
    
    # Extract terms from graph
    terms_data = extract_terms(graph)
    
    stats = {'added': 0, 'updated': 0, 'skipped': 0}
    
    for term_data in terms_data:
        concept_id = term_data['concept_id']
        
        if concept_id in existing_terms:
            if update_existing:
                # Update existing term
                term = existing_terms[concept_id]
                term.pref_label_es = term_data['pref_label_es'] or term.pref_label_es
                term.pref_label_en = term_data['pref_label_en'] or term.pref_label_en
                term.definition_es = term_data['definition_es'] or term.definition_es
                term.definition_en = term_data['definition_en'] or term.definition_en
                if term_data['alt_labels']:
                    term.alt_labels = term_data['alt_labels']
                if term_data['broader']:
                    term.broader = term_data['broader']
                if term_data['narrower']:
                    term.narrower = term_data['narrower']
                if term_data['related']:
                    term.related = term_data['related']
                if term_data['exact_match']:
                    term.exact_match = term_data['exact_match']
                if term_data['close_match']:
                    term.close_match = term_data['close_match']
                if term_data['source']:
                    term.source = term_data['source']
                stats['updated'] += 1
            else:
                stats['skipped'] += 1
        else:
            if add_new:
                # Create new term
                term = Term(
                    vocab_id=vocab_id,
                    concept_id=concept_id,
                    pref_label_es=term_data['pref_label_es'],
                    pref_label_en=term_data['pref_label_en'],
                    definition_es=term_data['definition_es'],
                    definition_en=term_data['definition_en'],
                    alt_labels=term_data['alt_labels'] if term_data['alt_labels'] else None,
                    broader=term_data['broader'] if term_data['broader'] else None,
                    narrower=term_data['narrower'] if term_data['narrower'] else None,
                    related=term_data['related'] if term_data['related'] else None,
                    exact_match=term_data['exact_match'] if term_data['exact_match'] else None,
                    close_match=term_data['close_match'] if term_data['close_match'] else None,
                    source=term_data['source']
                )
                db.session.add(term)
                stats['added'] += 1
            else:
                stats['skipped'] += 1
    
    db.session.commit()
    return stats


def detect_format(filename):
    """Detect RDF format from filename extension."""
    filename = filename.lower()
    if filename.endswith('.ttl'):
        return 'turtle'
    elif filename.endswith('.jsonld') or filename.endswith('.json'):
        return 'json-ld'
    elif filename.endswith('.rdf') or filename.endswith('.xml'):
        return 'xml'
    else:
        return 'xml'  # Default to RDF/XML
