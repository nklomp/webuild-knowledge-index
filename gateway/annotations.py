"""Validate project-owned annotation overrides without modifying source decisions."""
def validate_annotation(annotation,source):
    if annotation['source_revision']!=source['revision']:raise ValueError('Annotation revision mismatch')
    if not annotation.get('model') or not annotation.get('prompt_version'):raise ValueError('Missing provenance')
    for claim in annotation['claims']:
        if not claim.get('evidence') or any(span not in source['text'] for span in claim['evidence']):raise ValueError('Unsupported annotation')
        if claim.get('relationship') in ['implements','supersedes','changes','raises-concern-about'] and claim.get('confirmation')!='source-evidence':claim['status']='candidate'
    return annotation
