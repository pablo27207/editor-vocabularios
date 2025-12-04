import os
from rdflib import Graph, Namespace, RDF, SKOS, URIRef, Literal
from models import db, Vocabulary, Term
from flask import current_app

def load_rdf_file(file_path):
    g = Graph()
    g.parse(file_path)
    
    # Define Namespaces
    # Assuming standard SKOS
    
    # 1. Find the ConceptScheme (Vocabulary)
    scheme_node = None
    for s, p, o in g.triples((None, RDF.type, SKOS.ConceptScheme)):
        scheme_node = s
        break
    
    if not scheme_node:
        print(f"No ConceptScheme found in {file_path}")
        return

    # Extract Vocab Metadata
    vocab_name = str(g.value(scheme_node, SKOS.prefLabel) or g.value(scheme_node, URIRef("http://purl.org/dc/elements/1.1/title")))
    vocab_desc = str(g.value(scheme_node, SKOS.definition) or g.value(scheme_node, URIRef("http://purl.org/dc/elements/1.1/description")) or "")
    
    # Generate a code from filename or URI if not present
    filename = os.path.basename(file_path)
    vocab_code = filename.replace('.rdf', '').replace(' ', '_').upper()
    
    # Check if exists
    vocab = Vocabulary.query.filter_by(code=vocab_code).first()
    if not vocab:
        vocab = Vocabulary(
            code=vocab_code,
            name=vocab_name,
            description=vocab_desc,
            base_uri=str(scheme_node)
        )
        db.session.add(vocab)
        db.session.commit()
        print(f"Created Vocabulary: {vocab.name}")
    else:
        print(f"Updating Vocabulary: {vocab.name}")
        vocab.name = vocab_name
        vocab.description = vocab_desc
        vocab.base_uri = str(scheme_node)
        db.session.commit()

    # 2. Extract Concepts (Terms)
    for s, p, o in g.triples((None, RDF.type, SKOS.Concept)):
        # Skip if it's the scheme itself (sometimes happens in loose RDF)
        if s == scheme_node:
            continue
            
        # Concept ID (last part of URI)
        concept_id = str(s).split('/')[-1]
        
        # Labels (ES/EN)
        pref_label_es = None
        pref_label_en = None
        for label in g.objects(s, SKOS.prefLabel):
            if label.language == 'es':
                pref_label_es = str(label)
            elif label.language == 'en':
                pref_label_en = str(label)
        
        # Definitions
        definition_es = None
        definition_en = None
        for definition in g.objects(s, SKOS.definition):
            if definition.language == 'es':
                definition_es = str(definition)
            elif definition.language == 'en':
                definition_en = str(definition)

        # Broader/Narrower/Related (Store URIs or IDs)
        broader_list = []
        for broader in g.objects(s, SKOS.broader):
            broader_list.append(str(broader).split('/')[-1]) # Storing ID for now
            
        narrower_list = []
        for narrower in g.objects(s, SKOS.narrower):
            narrower_list.append(str(narrower).split('/')[-1])

        related_list = []
        for related in g.objects(s, SKOS.related):
            related_list.append(str(related).split('/')[-1])
            
        # Alt Labels
        alt_labels = []
        for alt in g.objects(s, SKOS.altLabel):
            alt_labels.append({'label': str(alt), 'lang': alt.language})

        # Check if term exists
        term = Term.query.filter_by(vocab_id=vocab.id, concept_id=concept_id).first()
        if not term:
            term = Term(
                vocab_id=vocab.id,
                concept_id=concept_id,
                pref_label_es=pref_label_es,
                pref_label_en=pref_label_en,
                definition_es=definition_es,
                definition_en=definition_en,
                broader=broader_list,
                narrower=narrower_list,
                related=related_list,
                alt_labels=alt_labels,
                status='approved'
            )
            db.session.add(term)
        else:
            term.pref_label_es = pref_label_es
            term.pref_label_en = pref_label_en
            term.definition_es = definition_es
            term.definition_en = definition_en
            term.broader = broader_list
            term.narrower = narrower_list
            term.related = related_list
            term.alt_labels = alt_labels
    
    db.session.commit()
    print(f"Imported terms for {vocab.name}")

def import_all_rdf(directory):
    for filename in os.listdir(directory):
        if filename.endswith(".rdf"):
            file_path = os.path.join(directory, filename)
            print(f"Processing {file_path}...")
            load_rdf_file(file_path)
