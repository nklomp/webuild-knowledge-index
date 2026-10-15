import json
from pathlib import Path
from gateway.model import record,digest

ORIGINAL_QUESTION='How does WeBuild govern architecture and implementation conformance?'
ORIGINAL_SOURCE='blueprint/07-governance-and-adr.md'

def test_governance_original_expected_source_regression(stores):
    writer,reader,_=stores
    # Fixture drawn from the pinned governance document, not a rewritten expected answer.
    text=('# Architecture Governance: ADRs and WBCS\nArchitectural Decision Records capture significant technical choices and rationale.\n'
          'WE BUILD Conformance Specifications define implementation requirements and exact interfaces for wallets, issuers and verifiers.\n'
          'The project uses a technical governance model based on clear documentation.')
    corpus=[record('governance','source-sha','https://github.com/webuild-consortium/wp4-architecture/blob/a78fb62ef8cd037b5038ef1418bb26f1d902995e/'+ORIGINAL_SOURCE,text,'architecture',path=ORIGINAL_SOURCE,permissions='full-text')]
    # A long policy document should not win simply because a term is repeated many times.
    corpus += [record('policy'+str(i),'sha','https://github.com/o/r/blob/sha/policy'+str(i)+'.md',('WeBuild implementation compliance policy '+str(i)+'\n')*40,'policies',path='policy'+str(i)+'.md',permissions='full-text') for i in range(12)]
    sid=writer.publish(corpus,{'coverage':[{'state':'complete'}]})
    result=reader.search(ORIGINAL_QUESTION,snapshot=sid,limit=10)
    assert result['ranking_version']=='weighted-fts-rrf-v4'
    assert ORIGINAL_SOURCE in [r['source']['locator'] for r in result['results']]
    assert result['results'][0]['source']['locator']==ORIGINAL_SOURCE

def test_authzen_archival_limitation_stays_attached(stores):
    writer,reader,_=stores;proof=json.loads(Path('config/source-evidence.json').read_text())[0]
    text='Status: accepted\nHistorical key binding at time T remains unresolved. Until the cited draft has a query-time extension, the archival case remains open.'
    source=record('authzen-archival','pinned',proof['url'],text,'architecture',path='adr/eaa-key-binding-authzen.md',permissions='full-text')
    writer.publish([source],{'coverage':[{'state':'complete'}]})
    result=reader.search('historical issuer key binding archival time')
    got=result['results'][0]['source']
    assert got['id']==source['id'] and got['decision_status']=='accepted'
    assert any('archival case remains open' in q for q in got['unresolved_questions'])
    assert got['url']==proof['url']

def test_etsi_report_is_not_an_official_correction(stores):
    writer,reader,_=stores;proof=json.loads(Path('config/source-evidence.json').read_text())[1]
    source=record('etsi-concern',proof['source_revision'],proof['url'],'ETSI TS 119 602 V1.1.1 (2025-11)\nReported schema vs PDF discrepancy; clause 6.3.5.\nOpen question: reconcile the discrepancy.','trust',kind='issue',lifecycle='closed',permissions='full-text')
    writer.publish([source],{'coverage':[{'state':'complete'}]})
    got=reader.search('ETSI schema PDF',version='1.1.1')['results'][0]['source']
    assert got['role']=='reported-concern' and got['decision_status']=='unknown' and got['lifecycle']=='closed'
    assert got['reported_concerns'] and got['unresolved_questions']
    assert got['specifications'][0]['cited_version']=='1.1.1' and got['specifications'][0]['upstream_version'] is None
    assert '6.3.5' in got['specifications'][0]['clause_identifiers']
