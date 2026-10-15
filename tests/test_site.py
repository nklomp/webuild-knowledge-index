"""Human-facing wiki presentation. Needs no database: generation works from exported records."""
import json
from gateway.model import record,digest
from gateway.site import generate
from gateway import presentation as p

MANIFEST={'snapshot':'snap-1','published_at':'2026-10-15T00:00:00+00:00'}
ARCH='webuild-consortium/wp4-architecture'

def corpus():
    adr=record('github:1:file:adr/key-binding.md','sha1','https://github.com/'+ARCH+'/blob/sha1/adr/key-binding.md','# Verify key binding\n\nStatus: accepted\n\nSee [the blueprint](../blueprint/README.md) and ![diagram](img/flow.png).\n<script>alert(1)</script>',ARCH,path='adr/key-binding.md',permissions='full-text')
    issue=record('github:I_1','sha2','https://github.com/'+ARCH+'/issues/7','Keys are unclear',ARCH,kind='issue',lifecycle='open',permissions='full-text')
    issue['title']='Clarify key binding'
    reply=record('github:IC_1','sha3','https://github.com/'+ARCH+'/issues/7#issuecomment-1','I agree with this.',ARCH,kind='comment',permissions='full-text')
    reply['title']='Clarify key binding (comment)'
    discussion=record('github:D_kwXYZ','sha4','https://github.com/'+ARCH+'/discussions/202','',ARCH,kind='discussion',lifecycle='open')
    rfc=record('external:abc123','sha5','https://www.rfc-editor.org/rfc/rfc9162','','external-specifications',kind='external-reference')
    rfc['title']=rfc['id']
    return [adr,issue,reply,discussion,rfc]

def test_titles_are_human_readable():
    adr,issue,reply,discussion,rfc=corpus()
    assert p.display_title(adr)=='Verify key binding'
    assert p.display_title(reply)=='Clarify key binding'
    assert p.display_title(discussion)=='Discussion #202'
    assert p.display_title(rfc)=='RFC 9162'
    assert p.display_title({'id':'x','kind':'external-reference','title':'x','url':'https://www.etsi.org/deliver/etsi_en/319400_319499/31941201/01.06.01_60/en_31941201v010601c.pdf'})=='ETSI EN 319 412-1 V1.6.1'
    assert p.display_title({'id':'x','kind':'external-reference','title':'x','url':'https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:32024R1183'})=='Regulation (EU) 2024/1183'
    assert p.repository_label('webuild-consortium/BU3')=='BU3'

def test_site_is_browsable_and_hides_technical_keys(tmp_path):
    records=corpus()
    generate(records,MANIFEST,tmp_path,'https://api.example.org')
    index=(tmp_path/'index.html').read_text(encoding='utf-8')
    repo=(tmp_path/'repo-webuild-consortium-wp4-architecture.html').read_text(encoding='utf-8')
    for raw in ['github:D_kwXYZ','external:abc123','github:IC_1']:
        assert raw not in index and raw not in repo
    assert 'Discussion #202' in repo and 'Verify key binding' in repo
    # Replies are nested in their thread instead of being listed on their own.
    assert 'I agree with this.' in (tmp_path/(digest('github:I_1')[:24]+'.html')).read_text(encoding='utf-8')
    catalog=json.loads((tmp_path/'catalog.json').read_text(encoding='utf-8'))
    assert {item[0] for item in catalog['items']}=={digest(r['id'])[:24]+'.html' for r in records if r['kind']!='comment'}
    page=(tmp_path/(digest('github:1:file:adr/key-binding.md')[:24]+'.html')).read_text(encoding='utf-8')
    tech=page.index('<details class="tech">')
    assert page.index('github:1:file:adr/key-binding.md')>tech
    assert '&lt;script&gt;alert(1)' in page and '<script>alert' not in page
    # Relative links resolve to the original source; images are linked, never embedded.
    assert 'href="https://github.com/'+ARCH+'/blob/sha1/blueprint/README.md"' in page and '<img' not in page
    assert json.loads((tmp_path/'verification.json').read_text())['navigation_valid']
    # Local publication verifies the served home page carries the snapshot identity.
    assert MANIFEST['snapshot'] in index
