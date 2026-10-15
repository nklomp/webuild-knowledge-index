import os,time
from typing import Any
from contextlib import asynccontextmanager
from collections import OrderedDict,deque
from fastapi import FastAPI,Request,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from .store import Store
from .embeddings import Embeddings

def create_app(store):
    with store.connect() as connection:
        role=connection.execute("SELECT current_user AS name,current_setting('transaction_read_only') AS readonly,has_table_privilege(current_user,'public.records','INSERT') AS can_write,pg_has_role(current_user,'gateway_ingest','MEMBER') AS writer_member").fetchone()
        if role['readonly']!='on' or role['can_write'] or role['writer_member']:raise ValueError('Retrieval must use an independent read-only database role')
    mcp=MCPServer('WeBuild read-only retrieval',version='0.1.0')
    annotation=ToolAnnotations(read_only_hint=True,destructive_hint=False,idempotent_hint=True,open_world_hint=False)
    @mcp.tool(annotations=annotation,structured_output=True)
    def search(q:str,snapshot:str|None=None,status:str|None=None,version:str|None=None,scope:str|None=None,offset:int=0,limit:int=20)->dict[str,Any]:
        return store.search(q,snapshot,status,version,scope,offset,limit)
    @mcp.tool(annotations=annotation,structured_output=True)
    def get_source(id:str,snapshot:str|None=None)->dict[str,Any]:return store.source(id,snapshot)
    @mcp.tool(annotations=annotation,structured_output=True)
    def get_related_sources(id:str|None=None,topic:str|None=None,snapshot:str|None=None,offset:int=0,limit:int=100,specs:bool=False)->dict[str,Any]:return store.related(id,topic,snapshot,specs,offset=offset,limit=limit)
    @mcp.tool(annotations=annotation,structured_output=True)
    def get_related_specs(id:str,snapshot:str|None=None,offset:int=0,limit:int=100)->dict[str,Any]:return store.related(id,None,snapshot,True,offset,limit)
    @mcp.tool(annotations=annotation,structured_output=True)
    def get_decision_history(id:str,offset:int=0,limit:int=100,snapshot:str|None=None)->dict[str,Any]:return store.history(id,offset,limit,snapshot)
    @mcp.tool(annotations=annotation,structured_output=True)
    def get_changes(before:str,after:str|None=None,offset:int=0,limit:int=100)->dict[str,Any]:return store.changes(before,after,offset,limit)
    transport=mcp.streamable_http_app(stateless_http=True,json_response=True,host=os.getenv('SERVICE_HOST') or os.getenv('RENDER_EXTERNAL_HOSTNAME','127.0.0.1'))
    @asynccontextmanager
    async def lifespan(app):
        async with transport.router.lifespan_context(transport):yield
    app=FastAPI(title='WeBuild retrieval',lifespan=lifespan)
    origins=os.getenv('ALLOWED_ORIGINS','http://localhost:8080').split(',')
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET'],allow_headers=['Content-Type'])
    buckets=OrderedDict()
    @app.middleware('http')
    async def limits(request:Request,call_next):
        from starlette.responses import JSONResponse
        origin=request.headers.get('origin')
        if origin and origin not in origins:return JSONResponse({'detail':'Origin not allowed'},403)
        if request.url.path.startswith('/v1/') and request.method not in ['GET','OPTIONS']:return JSONResponse({'detail':'Read only'},405)
        key=request.client.host
        if key not in buckets:
            if len(buckets)>=10000:buckets.popitem(last=False)
            buckets[key]=deque()
        buckets.move_to_end(key);bucket=buckets[key];t=time.monotonic()
        while bucket and bucket[0]<t-60:bucket.popleft()
        if len(bucket)>=120:return JSONResponse({'detail':'Rate limit'},429)
        bucket.append(t)
        response=await call_next(request);response.headers['X-Content-Type-Options']='nosniff';return response
    @app.exception_handler(LookupError)
    async def missing(request,e):
        from starlette.responses import JSONResponse
        return JSONResponse({'detail':str(e)},404)
    @app.exception_handler(ValueError)
    async def invalid(request,e):
        from starlette.responses import JSONResponse
        return JSONResponse({'detail':str(e)},400)
    app.get('/v1/search')(search)
    app.get('/v1/sources/{id:path}')(get_source)
    app.get('/v1/relations')(get_related_sources)
    app.get('/v1/decisions/{id:path}/history')(get_decision_history)
    app.get('/v1/changes')(get_changes)
    @app.get('/v1/manifest')
    def manifest(snapshot:str|None=None):return store.manifest(snapshot)
    @app.get('/live')
    def live():
        # Platform startup probes must work before the first index publication.
        # Freshness and source coverage are checked separately by /health.
        return {'status':'live'}
    @app.get('/health')
    def health():
        from datetime import datetime,timezone
        m=store.manifest();age=(datetime.now(timezone.utc)-datetime.fromisoformat(m['published_at'])).total_seconds()
        from starlette.responses import JSONResponse
        latest=store.latest_run() or m['coverage'];entries=latest.get('coverage',[])
        failed=[s for s in entries if s['state'] in ['failed','partial']]
        stale=[]
        for entry in entries:
            stamp=entry.get('captured_at')
            if stamp and (datetime.now(timezone.utc)-datetime.fromisoformat(stamp.replace('Z','+00:00'))).total_seconds()>36*3600:stale.append(entry.get('repository',entry.get('source')))
        unhealthy=age>36*3600 or bool(failed) or bool(stale)
        return JSONResponse({'snapshot':m['snapshot'],'age_seconds':age,'latest_ingestion':latest,'failed_sources':failed,'stale_sources':stale,'freshness_failure':unhealthy},status_code=503 if unhealthy else 200)
    import psycopg
    @app.exception_handler(psycopg.errors.QueryCanceled)
    async def timeout(request,error):
        from starlette.responses import JSONResponse
        return JSONResponse({'detail':'Retrieval query timed out'},503)
    app.mount('/',transport)
    return app

def factory():return create_app(Store(os.environ['RETRIEVAL_DATABASE_URL'],Embeddings()))
