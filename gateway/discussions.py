"""Read-only GitHub GraphQL discussion adapter; every nested connection is paginated."""
import json,os
from .model import record,digest
class Discussions:
    def __init__(self,client):self.client=client
    def query(self,query,variables):
        if not query.lstrip().startswith('query') or 'mutation' in query:raise ValueError('Only GraphQL queries allowed')
        if hasattr(self.client,'graphql'):return self.client.graphql(query,variables)
        token=os.environ['SOURCE_READ_TOKEN']
        r=self.client.post('https://api.github.com/graphql',json={'query':query,'variables':variables},headers={'Authorization':'Bearer '+token});r.raise_for_status();data=r.json()
        if data.get('errors'):raise RuntimeError(json.dumps(data['errors']))
        return data['data']
    def capture(self,repo,permission):
        owner,name=repo.split('/');cursor=None;seen=set();rows=[];counts={'discussions':0,'discussion_comments':0,'discussion_replies':0}
        while True:
            if cursor in seen:raise ValueError('Repeated discussion cursor')
            seen.add(cursor)
            data=self.query('''query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){discussions(first:100,after:$cursor){nodes{id title body url updatedAt closed} pageInfo{hasNextPage endCursor}}}}''',{'owner':owner,'name':name,'cursor':cursor})
            conn=data['repository']['discussions']
            for discussion in conn['nodes']:
                rows.append(record('github:'+discussion['id'],digest(json.dumps(discussion,sort_keys=True)),discussion['url'],discussion['title']+'\n'+discussion['body'],repo,'discussion',lifecycle='closed' if discussion['closed'] else 'open',updated=discussion['updatedAt'],permissions=permission));counts['discussions']+=1
                comment_cursor=None;comment_seen=set()
                while True:
                    if comment_cursor in comment_seen:raise ValueError('Repeated discussion comment cursor')
                    comment_seen.add(comment_cursor)
                    comments=self.query('''query($id:ID!,$cursor:String){node(id:$id){... on Discussion{comments(first:100,after:$cursor){nodes{id body url updatedAt} pageInfo{hasNextPage endCursor}}}}}''',{'id':discussion['id'],'cursor':comment_cursor})['node']['comments']
                    for comment in comments['nodes']:
                        rows.append(record('github:'+comment['id'],digest(json.dumps(comment,sort_keys=True)),comment['url'],comment['body'],repo,'discussion-comment',updated=comment['updatedAt'],permissions=permission));counts['discussion_comments']+=1
                        rows[-1].update(parent_id='github:'+discussion['id'],title=discussion['title']+' (discussion comment)',context_url=discussion['url'])
                        reply_cursor=None;reply_seen=set()
                        while True:
                            if reply_cursor in reply_seen:raise ValueError('Repeated discussion reply cursor')
                            reply_seen.add(reply_cursor)
                            replies=self.query('''query($id:ID!,$cursor:String){node(id:$id){... on DiscussionComment{replies(first:100,after:$cursor){nodes{id body url updatedAt} pageInfo{hasNextPage endCursor}}}}}''',{'id':comment['id'],'cursor':reply_cursor})['node']['replies']
                            for reply in replies['nodes']:
                                rows.append(record('github:'+reply['id'],digest(json.dumps(reply,sort_keys=True)),reply['url'],reply['body'],repo,'discussion-reply',updated=reply['updatedAt'],permissions=permission));counts['discussion_replies']+=1
                                rows[-1].update(parent_id='github:'+comment['id'],title=discussion['title']+' (reply)',context_url=discussion['url'])
                            if not replies['pageInfo']['hasNextPage']:break
                            reply_cursor=replies['pageInfo']['endCursor']
                    if not comments['pageInfo']['hasNextPage']:break
                    comment_cursor=comments['pageInfo']['endCursor']
            if not conn['pageInfo']['hasNextPage']:break
            cursor=conn['pageInfo']['endCursor']
        return rows,counts
