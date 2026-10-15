import io,json,tarfile
import httpx,pytest
from gateway.http import ReadClient,CaptureJournal
from gateway.review_threads import capture_threads
from gateway.official import capture as official_capture
from gateway.tags import capture_tags
from gateway.extraction import entities,parse_file,specifications

def test_review_thread_and_nested_reply_pagination(tmp_path):
    calls=[]
    def connection(nodes,cursor=None):return {'nodes':nodes,'pageInfo':{'hasNextPage':cursor is not None,'endCursor':cursor}}
    def handle(req):
        body=json.loads(req.content);v=body['variables'];q=body['query'];calls.append(v)
        if 'reviewThreads' in q:
            result={'repository':{'pullRequest':{'reviewThreads':connection([{'id':'T','isResolved':True,'isOutdated':True,'path':'a.md','line':3,'startLine':2,'resolvedBy':{'login':'reviewer'}}] if v['cursor'] is None else [],'thread-next' if v['cursor'] is None else None)}}}
        else:
            result={'node':{'comments':connection([{'id':'c1' if v['cursor'] is None else 'c2','body':'Unresolved concern remains','url':'https://github.com/o/r/pull/1#discussion_r1','updatedAt':'2026-10-01T00:00:00Z','replyTo':None if v['cursor'] is None else {'id':'c1'},'author':{'login':'someone'}}],'comment-next' if v['cursor'] is None else None)}}
        return httpx.Response(200,json={'data':result})
    reader=ReadClient(httpx.Client(transport=httpx.MockTransport(handle)),CaptureJournal(tmp_path/'j.sqlite'),token='[REDACTED_SECRET]')
    rows=list(capture_threads(reader,'o/r',1,'metadata-only'))
    assert len(calls)==4 and len(rows)==1 and len(rows[0]['contributions'])==2
    assert rows[0]['thread_state']['isResolved'] is True
    assert rows[0]['decision_status']=='unknown' and rows[0]['unresolved_questions']
    assert rows[0]['contributions'][1]['reply_to']=={'id':'c1'}

def test_official_html_discards_script_and_preserves_clauses():
    client=httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,text='<h1 id="title">OpenID OID4VP 1.0</h1><script>doBadThings()</script><h2 id="clause-4">Clause 4.1</h2><p>Specification content.</p>',headers={'content-type':'text/html'})))
    source=official_capture({'url':'https://openid.net/specs/v1.html','identity':'OID4VP','version':'1.0','document_type':'technical-specification','mode':'fetch'},ReadClient(client,allowed_hosts=['openid.net']))
    assert 'doBadThings' not in source['text'] and source['edition_version']=='1.0'
    assert source['source_sections'][1]['anchor']=='clause-4' and source['reuse_permissions']=='metadata-only'

def test_configured_version_is_distinct_from_extracted_version():
    reader=ReadClient(httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,text='OID4VP 1.0',headers={'content-type':'text/plain'}))),allowed_hosts=['openid.net'])
    source=official_capture({'url':'https://openid.net/v1','identity':'OID4VP','version':'2.0','mode':'fetch'},reader)
    assert source['specifications'][0]['cited_version']=='1.0'
    assert source['edition_version']=='2.0' and not source['provenance']['catalogue_metadata']['verified_against_body']

def test_jsonld_and_schema_entities_are_not_remote_fetches():
    text=json.dumps({'@context':'https://evil.test/context','@id':'https://example.org/ebwv#Company','skos:prefLabel':'Company','skos:altLabel':['Business'],'properties':{'legalName':{'description':'Legal name of a company'}}})
    result=entities(text,'vocab.jsonld')
    assert result[0]['id']=='https://example.org/ebwv#Company' and result[0]['aliases']==['Business']
    assert any(r['locator']=='/properties/legalName' for r in result)

def test_pdf_text_page_provenance():
    from pypdf import PdfWriter
    out=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.write(out)
    text,provenance=parse_file(out.getvalue(),'edition.pdf')
    assert provenance['pages']==1 and provenance['ocr'] is False and '<!-- page 1 -->' in text

def test_exact_specification_and_official_link_not_guessed():
    spec=specifications('ETSI TS 119 602 V1.1.1; clause 6.3.5.')
    assert spec[0]['cited_version']=='1.1.1' and spec[0]['official_url'] is None
    assert spec[0]['clause_identifiers']==['6.3.5']

def test_tag_pages_preserve_independent_editions():
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
        data=b'# ARF\nARF 1.0.0\n';member=tarfile.TarInfo('r-sha/README.md');member.size=len(data);tar.addfile(member,io.BytesIO(data))
    def handle(req):
        if req.url.path.endswith('/tags'):
            page=req.url.params.get('page');return httpx.Response(200,json=[{'name':'v2' if page else 'v1','commit':{'sha':'sha'}}],headers={} if page else {'Link':'<https://api.github.com/repos/o/r/tags?page=2>; rel="next"'})
        if '/git/trees/' in req.url.path:return httpx.Response(200,json={'tree':[{'type':'blob','path':'README.md','sha':'blob'}]})
        return httpx.Response(200,content=buffer.getvalue())
    rows,editions=capture_tags(ReadClient(httpx.Client(transport=httpx.MockTransport(handle))),'o/r',1,'metadata-only',['README.md'])
    assert len(rows)==2 and rows[0]['id']!=rows[1]['id'] and rows[0]['revision']=='blob'
    assert [e['tag'] for e in editions]==['v1','v2'] and all(r['edition_status']=='tagged-edition' for r in rows)

def test_etsi_and_openid_url_encoded_versions():
    from gateway.catalogue import references
    from gateway.model import record
    text='https://www.etsi.org/deliver/etsi_ts/119600_119699/119602/01.01.01_60/ts_119602v010101p.pdf\nhttps://openid.net/specs/authorization-api-1_0.html'
    rows=references([record('x','sha','https://github.com/o/r/blob/sha/a.md',text,'r')],['www.etsi.org','openid.net'])
    assert {r['specifications'][0]['cited_version'] for r in rows}=={'1.1.1','1.0'}
    assert all(r['specifications'][0]['upstream_version'] is None for r in rows)
