import os
import pytest,psycopg
from gateway.embeddings import Embeddings
from gateway.store import Store
from gateway.model import record
@pytest.fixture(scope='session')
def embeddings():return Embeddings()
@pytest.fixture
def corpus():
    r=[record('authzen','sha-auth','https://github.com/webuild-consortium/wp4-architecture/blob/sha/adr/authzen.md','Status: accepted\nAuthZEN key binding decision. Historical key binding queries remain unresolved. References OpenID OID4VP 1.0 https://openid.net/specs/openid-4-verifiable-presentations-1_0.html','architecture',path='adr/authzen.md',lifecycle='merged',permissions='full-text'),
    record('proposal','sha-proposal','https://github.com/webuild-consortium/wp4-architecture/blob/sha/adr/proposal.md','Status: draft\nA proposal for authorization with ETSI TS 119 462 V1.2.1.','architecture',path='adr/proposal.md',lifecycle='merged',permissions='full-text'),
    record('closed','sha-closed','https://github.com/webuild-consortium/wp4-trust-group/issues/104','ETSI schema PDF discrepancy reported. Open question: how to reconcile?','trust',kind='issue',lifecycle='closed',permissions='full-text'),
    record('ebwv','sha-ebwv','https://github.com/webuild-consortium/wp4-semantics-group/blob/sha/vocab/README.md','European Business Wallet Vocabulary EBWV defines business terminology.','semantics',path='vocab/README.md',permissions='full-text'),
    record('rulebook','sha-rulebook','https://github.com/webuild-consortium/webuild-attestation-rulebooks-catalog/blob/sha/rulebook.md','Conformance rulebook schema for business attestations.','rulebooks',path='rulebook.md',permissions='full-text')]
    return r
@pytest.fixture
def stores(embeddings,corpus):
    with psycopg.connect(os.environ['ADMIN_DATABASE_URL']) as c:c.execute('TRUNCATE publication,relations,revoked,chunks,ingestion_runs,publication_events,restoration_events,records,snapshots CASCADE')
    writer=Store(os.environ['INGEST_DATABASE_URL'],embeddings);reader=Store(os.environ['RETRIEVAL_DATABASE_URL'],embeddings)
    sid=writer.publish(corpus,{'coverage':[{'repository':'fixture','state':'complete','captured_at':'2026-10-07T00:00:00Z'}],'purpose':'controlled regression fixture'})
    return writer,reader,sid
