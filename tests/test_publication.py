import pytest
from gateway.api import create_app
from gateway.model import digest

def test_prepare_failure_and_compare_swap_promotion(stores,corpus):
    writer,reader,old=stores
    corpus[0]['text']+='\nChanged';corpus[0]['content_hash']=digest(corpus[0]['text']);corpus[0]['revision']='new'
    staged=writer.publish(corpus,{'coverage':[{'state':'complete'}]},promote=False)
    assert reader.manifest()['snapshot']==old and reader.source('authzen',staged)['source']['revision']=='new'
    # Failed Pages deployment makes no call to promote; latest remains the prior complete index.
    writer.promote(staged);assert reader.manifest()['snapshot']==staged
    writer.promote(old,expected_current=staged,rollback=True);assert reader.manifest()['snapshot']==old
    writer.promote(staged,expected_current=old)
    with pytest.raises(ValueError):writer.promote(old,expected_current=old)

def test_stale_capture_cannot_resurrect_withdrawn_source(stores,corpus):
    writer,reader,old=stores;withdrawn,_=writer.quarantine(['architecture'],{})
    stale=writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    with pytest.raises(LookupError):reader.source('authzen',stale)
    writer.restore_public('authzen',corpus[0]['url'],'Explicit public verification in operator fixture')
    assert reader.source('authzen',stale)['source']['id']=='authzen'

def test_canonical_export_after_rename(stores,corpus):
    writer,reader,_=stores;corpus[0].update(id='moved',locator='adr/renamed.md')
    sid=writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    assert any(r['id']=='authzen' and r['locator']=='adr/renamed.md' for r in writer.export_records(sid))
    assert all(r['id']!='moved' for r in writer.export_records(sid))
    assert writer.publish(corpus,{'coverage':[{'state':'complete'}]})==sid

def test_factory_rejects_writer_credentials(stores):
    writer,_,_=stores
    with pytest.raises(ValueError,match='read-only'):create_app(writer)

def test_metadata_only_changes_are_in_snapshot_diff(stores,corpus):
    writer,reader,old=stores;corpus[0]['decision_status']='unknown';corpus[0]['status_evidence']=None
    sid=writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    assert 'authzen' in [r['id'] for r in reader.changes(old,sid)['changes']]

def test_empty_page_retains_total(stores):
    _,reader,_=stores;r=reader.search('wallet',offset=100)
    assert r['results']==[] and r['total']==5

def test_identical_source_with_only_extraction_time_change_is_not_content_change(stores,corpus):
    writer,reader,old=stores
    corpus[0]['provenance']['extracted_at']='2026-10-15T00:00:00Z'
    sid=writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    assert not any(r['id']=='authzen' for r in reader.changes(old,sid)['changes'])

def test_history_pins_to_snapshot(stores,corpus):
    writer,reader,old=stores;corpus[0]['revision']='changed'
    sid=writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    assert len(reader.history('authzen',snapshot=old)['history'])==1
    assert len(reader.history('authzen',snapshot=sid)['history'])==2
def test_withdrawal_sanitizes_shared_reference_provenance_in_old_snapshots(stores,corpus):
    import copy,json
    from gateway.catalogue import references
    from gateway.model import digest
    writer,reader,_=stores
    records=copy.deepcopy(corpus)
    official='https://openid.net/specs/openid-4-verifiable-presentations-1_0.html'
    records[3]['text']+='\nReference '+official
    records[3]['content_hash']=digest(records[3]['text'])
    external=references(records,['openid.net'])
    assert len(external)==1
    before=writer.publish(records+external,{'coverage':[{'repository':'architecture','state':'complete'},{'repository':'semantics','state':'complete'}]})
    after,_=writer.quarantine(['architecture'],{})
    for snapshot in [before,after]:
        public=reader.source(external[0]['id'],snapshot)['source']
        assert {p['id'] for p in public['provenance']['referenced_by']}=={'ebwv'}
        exported=next(r for r in writer.export_records(snapshot) if r['id']==external[0]['id'])
        assert {p['id'] for p in exported['provenance']['referenced_by']}=={'ebwv'}
        assert records[0]['url'] not in json.dumps(public)
        assert records[0]['url'] not in json.dumps(exported)
