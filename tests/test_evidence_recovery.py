import copy
import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('regenerate_source_evidence',Path('scripts/regenerate_source_evidence.py'))
regeneration=importlib.util.module_from_spec(spec)
spec.loader.exec_module(regeneration)


def test_recovered_fixture_copies_and_source_labels():
    config=json.loads(Path('config/source-evidence.json').read_text())
    assert config==json.loads(Path('tests/fixtures/source-evidence.json').read_text())
    assert [p['id'] for p in config]==['authzen-archival','etsi-104']
    assert all(p['evidence_label']=='source-derived; not a participant question' for p in config)
    assert 'not an official correction' in config[1]['attribution']


def test_regeneration_rejects_unverified_content():
    with pytest.raises(ValueError,match='AuthZEN content hash mismatch'):
        regeneration.proofs_from_sources('unverified substitute',{'title':'reported','body':'concern'})


def test_recovered_json_pointer_escaping():
    from gateway.extraction import entities
    text=json.dumps({'properties':{'a~/b':{'$id':'urn:example:escaped'}}})
    found=entities(text,'schema.json')
    assert next(e for e in found if e['id']=='a~/b')['locator']=='/properties/a~0~1b'
    assert next(e for e in found if e['id']=='urn:example:escaped')['locator']=='/properties/a~0~1b'


def test_recovered_discussion_token_lookup(monkeypatch):
    import httpx
    from gateway.discussions import Discussions
    monkeypatch.setenv('SOURCE_READ_TOKEN','test-only-source-read-sentinel')
    def handle(request):
        assert request.headers['Authorization']=='Bearer test-only-source-read-sentinel'
        assert request.url==httpx.URL('https://api.github.com/graphql')
        assert json.loads(request.content)['query'].lstrip().startswith('query')
        return httpx.Response(200,json={'data':{'repository':{'name':'fixture'}}})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        assert Discussions(client).query('query { repository { name } }',{})=={'repository':{'name':'fixture'}}


def test_weight_selection_never_queries_held_out_labels():
    from gateway.retrieval import calibrate_weight
    class TuningResults:
        semantic_weight=1.0
        def search(self,q,**kwargs):
            assert q=='original tuning question'
            return {'results':[{'source':{'locator':'expected.md'}}]}
    store=TuningResults()
    result=calibrate_weight(store,[
        {'split':'tuning','question':'original tuning question','expected_locator':'expected.md'},
        {'split':'held-out-v2','question':'must never tune on this','expected_locator':'other.md'},
    ],'controlled-snapshot')
    assert result['semantic_weight']==1.0 and store.semantic_weight==1.0
    assert result['tuning_questions']==['original tuning question']


def test_changed_context_reencodes_unchanged_section(stores,corpus):
    from gateway.model import digest,sections,record
    writer,reader,old=stores
    initial=copy.deepcopy(corpus)
    initial[0]=record('authzen','context-original',corpus[0]['url'],
        '# Original title\nStatus: accepted\n\n## Details\nUnchanged section content.',
        'architecture',path='adr/authzen.md',permissions='full-text')
    writer.publish(initial,{'coverage':[]})
    updated=copy.deepcopy(initial)
    updated[0]['text']=updated[0]['text'].replace('Original title','Revised contextual title')
    updated[0]['content_hash']=digest(updated[0]['text'])
    snapshot=writer.publish(updated,{'coverage':[]})
    piece=next(p for p in sections(updated[0]) if p['text'].startswith('## Details'))
    expected=writer.embed.encode([piece['context']+'\n'+piece['text']])[0]
    with writer.connect() as c:
        actual=json.loads(c.execute('SELECT embedding::text AS vector FROM chunks WHERE snapshot=%s AND source=%s AND content=%s',(snapshot,updated[0]['id'],piece['text'])).fetchone()['vector'])
    assert actual==pytest.approx(expected,abs=1e-7)
