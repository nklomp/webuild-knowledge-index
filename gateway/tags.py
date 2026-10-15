"""Official tagged editions. Stable tag/path IDs and immutable tree/blob revisions."""
import io,tarfile
from urllib.parse import quote
from .model import record
from .extraction import parse_file

def capture_tags(reader,repository,repository_id,permission,paths):
    root='https://api.github.com/repos/'+repository;rows=[];editions=[]
    for tag in reader.pages(root+'/tags?per_page=100'):
        edition=tag['name'];commit=tag['commit']['sha'];tree=reader.get(root+'/git/trees/'+commit+'?recursive=1').json()
        if tree.get('truncated'):raise ValueError('Truncated tagged tree')
        response=reader.get('https://codeload.github.com/'+repository+'/tar.gz/'+commit)
        count=0;links=0
        with tarfile.open(fileobj=io.BytesIO(response.content),mode='r:gz') as archive:
            members={m.name.split('/',1)[1]:m for m in archive.getmembers() if m.isfile() and '/' in m.name}
            for entry in tree['tree']:
                path=entry['path']
                if entry['type']!='blob' or not any(path==p or path.startswith(p) for p in paths):continue
                url=f'https://github.com/{repository}/blob/{commit}/'+quote(path,safe='/')
                kind='pdf' if path.lower().endswith('.pdf') else 'file'
                if entry.get('mode')=='120000':
                    # A symlink is a Git blob but not a regular archive member.
                    # Record its identity without reading or following its target.
                    text=path;kind='binary-metadata';links+=1
                    extraction={'method':'link-only','limitation':'symbolic link is never followed'}
                else:
                    member=members.get(path)
                    if member is None:raise ValueError('Tag archive/tree mismatch')
                    if member.size>10_000_000:raise ValueError('Tagged source exceeds size limit')
                    text,extraction=parse_file(archive.extractfile(member).read(),path)
                    if text is None:continue
                    count+=1
                item=record(f'github:{repository_id}:tag:{edition}:{path}',entry['sha'],url,text,repository,kind,path=path,permissions='metadata-only' if kind=='binary-metadata' else permission)
                item.update(edition_tag=edition,edition_commit=commit,edition_status='tagged-edition',repository_id=repository_id)
                item['provenance']['extraction']=extraction;item['provenance']['tag_url']='https://github.com/'+repository+'/releases/tag/'+quote(edition,safe='')
                rows.append(item)
        editions.append({'tag':edition,'commit':commit,'files':count,'symbolic_links':links})
    return rows,editions
