"""Read-only review threads, resolution/outdated flags and independently paginated comments."""
import json
from .model import record,digest

def capture_threads(reader,repo,number,permission):
    owner,name=repo.split('/');cursor=None;seen=set()
    while True:
        if cursor in seen:raise ValueError('Repeated review thread cursor')
        seen.add(cursor)
        data=reader.graphql('''query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100,after:$cursor){nodes{id isResolved isOutdated path line startLine resolvedBy{login}} pageInfo{hasNextPage endCursor}}}}}''',{'owner':owner,'name':name,'number':number,'cursor':cursor})
        connection=data['repository']['pullRequest']['reviewThreads']
        for thread in connection['nodes']:
            comments=[];comment_cursor=None;comment_seen=set()
            while True:
                if comment_cursor in comment_seen:raise ValueError('Repeated review comment cursor')
                comment_seen.add(comment_cursor)
                conn=reader.graphql('''query($id:ID!,$cursor:String){node(id:$id){... on PullRequestReviewThread{comments(first:100,after:$cursor){nodes{id body url updatedAt replyTo{id} author{login}} pageInfo{hasNextPage endCursor}}}}}''',{'id':thread['id'],'cursor':comment_cursor})['node']['comments']
                comments.extend(conn['nodes'])
                if not conn['pageInfo']['hasNextPage']:break
                comment_cursor=conn['pageInfo']['endCursor']
            url=comments[0]['url'] if comments else f'https://github.com/{repo}/pull/{number}'
            text='\n\n'.join(c['body'] for c in comments)
            item=record('github:'+thread['id'],digest(json.dumps([thread,comments],sort_keys=True)),url,text,repo,'review-thread',lifecycle='resolved' if thread['isResolved'] else 'unresolved',permissions=permission)
            item.update(title=f'PR #{number} review thread: {thread["path"]}',thread_state=thread,contributions=[{'id':'github:'+c['id'],'url':c['url'],'updated_at':c['updatedAt'],'reply_to':c.get('replyTo'),'author':c.get('author')} for c in comments])
            # Resolution is a GitHub thread state, never proof a reported concern is settled.
            item['provenance']['thread_state_source']='GitHub GraphQL reviewThreads';yield item
        if not connection['pageInfo']['hasNextPage']:break
        cursor=connection['pageInfo']['endCursor']
