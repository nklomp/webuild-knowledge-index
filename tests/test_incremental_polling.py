"""Controlled transport regressions; not evidence of a live historical crawl."""
import json
from datetime import datetime,timedelta,timezone

import httpx
import pytest

from gateway.ingest import GitHub,capture
from gateway.model import record
from test_ingestion_resume import fixture_api


def baseline():
    client,_=fixture_api()
    rows,coverage=GitHub(client).repo('o/r')
    return {'records':rows,'coverage':coverage}


def changed_client(*,issue_rows=None,comments=None,fail=False):
    client,requests=fixture_api()
    original=client._transport
    def handle(req):
        if req.url.path=='/repos/o/r/issues' and issue_rows is not None:
            requests.append(req)
            return httpx.Response(200,json=issue_rows)
        if req.url.path.endswith('/comments'):
            requests.append(req)
            if fail:return httpx.Response(429,headers={'Retry-After':'1000'})
            if comments is not None:return httpx.Response(200,json=comments)
        return original.handle_request(req)
    return httpx.Client(transport=httpx.MockTransport(handle)),requests


def test_overlap_retains_unchanged_evidence_without_refreshing_its_time():
    previous=baseline()
    old=next(r for r in previous['records'] if r['kind']=='comment')
    client,requests=changed_client(issue_rows=[])
    rows,coverage=GitHub(client).repo('o/r',previous)
    request=next(r for r in requests if r.url.path.endswith('/issues'))
    assert datetime.fromisoformat(request.url.params['since'])==datetime.fromisoformat(previous['coverage']['poll_cursor'])-timedelta(hours=1)
    assert next(r for r in rows if r['id']==old['id'])==old
    assert coverage['poll_mode']=='overlap' and coverage['counts']['issues']==1
    assert coverage['captured_at']==coverage['poll_cursor']
    assert coverage['oldest_record_retrieved_at']<=old['retrieved_at']
    assert not any(r.url.path.endswith('/comments') for r in requests)


def test_changed_parent_replaces_subtree_and_removes_deleted_comment():
    client,_=changed_client(comments=[])
    rows,coverage=GitHub(client).repo('o/r',baseline())
    assert coverage['poll_mode']=='overlap'
    assert coverage['counts']['comments']==0 and not any(r['kind']=='comment' for r in rows)


@pytest.mark.parametrize('reason',['weekly','identity','permissions','forced'])
def test_full_reconciliation_drops_removed_issues(reason):
    previous=baseline()
    if reason=='weekly':previous['coverage']['last_full_reconciliation']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()
    if reason=='identity':previous['coverage']['repository_id']=2
    if reason=='permissions':previous['coverage']['reuse_permissions']='metadata-only'
    client,requests=changed_client(issue_rows=[])
    rows,coverage=GitHub(client).repo('o/r',previous,force_full=reason=='forced')
    assert coverage['poll_mode']=='full-reconciliation'
    assert not any(r['kind'] in ('issue','comment') for r in rows)
    assert 'since' not in next(r for r in requests if r.url.path.endswith('/issues')).url.params


def test_failed_update_preserves_durable_baseline_and_cursor(tmp_path):
    cfg=tmp_path/'sources.json'
    cfg.write_text(json.dumps({'organization':'o','repositories':['r'],'initial':['r'],'allowed_reference_hosts':[],
                              'incremental_polling':{'enabled':True}}))
    healthy,_=fixture_api();capture(cfg,tmp_path/'owned',client=healthy)
    path=tmp_path/'owned/o__r.json';previous=path.read_bytes()
    broken,_=changed_client(fail=True)
    _,failed=capture(cfg,tmp_path/'owned',client=broken)
    assert failed['status']=='incomplete' and path.read_bytes()==previous
    healthy,requests=changed_client(comments=[])
    rows,completed=capture(cfg,tmp_path/'owned',client=healthy)
    assert completed['resumed'] and completed['status']=='complete'
    assert next(e for e in completed['coverage'] if e.get('repository')=='o/r')['poll_mode']=='overlap'
    assert not any(r['kind']=='comment' for r in rows)


def test_forced_full_reconciliation_remains_forced_after_restart(tmp_path):
    cfg=tmp_path/'sources.json'
    cfg.write_text(json.dumps({'organization':'o','repositories':['r'],'initial':['r'],'allowed_reference_hosts':[],
                              'incremental_polling':{'enabled':True}}))
    healthy,_=fixture_api();capture(cfg,tmp_path/'owned',client=healthy)
    broken,_=changed_client(fail=True)
    _,failed=capture(cfg,tmp_path/'owned',client=broken,force_full=True)
    assert failed['status']=='incomplete'
    healthy,_=changed_client(comments=[])
    _,completed=capture(cfg,tmp_path/'owned',client=healthy)
    assert completed['resumed'] and completed['status']=='complete'
    assert completed['coverage'][0]['poll_mode']=='full-reconciliation'


def test_overlap_follows_every_page_and_deduplicates_by_identity():
    previous=baseline();client,requests=fixture_api();original=client._transport
    def handle(req):
        if req.url.path=='/repos/o/r/issues':
            response=original.handle_request(req)
            if req.url.params.get('page')=='2':return response
            return httpx.Response(200,json=response.json(),headers={'Link':'<'+str(req.url)+'&page=2>; rel="next"'})
        return original.handle_request(req)
    rows,coverage=GitHub(httpx.Client(transport=httpx.MockTransport(handle))).repo('o/r',previous)
    assert coverage['updated_issues_fetched']==2
    assert len(rows)==len({r['id'] for r in rows})==3
    assert any(r.url.params.get('page')=='2' for r in requests)


def test_unchanged_pr_rechecks_reviews_and_drops_deleted_thread():
    previous=baseline()
    pull=record('github:P2','old','https://github.com/o/r/pull/2','A PR','o/r','pull',permissions='full-text')
    thread=record('github:T2','old','https://github.com/o/r/pull/2#thread','Old thread','o/r','review-thread',permissions='full-text')
    thread['parent_id']=pull['id'];previous['records'] += [pull,thread]
    client,requests=fixture_api();original=client._transport
    def handle(req):
        if req.url.path=='/repos/o/r/issues':return httpx.Response(200,json=[])
        if req.url.path=='/repos/o/r/issues/2':
            requests.append(req)
            return httpx.Response(200,json={'node_id':'P2','number':2,'pull_request':{},'state':'closed','updated_at':'2026-10-01T00:00:00Z',
                                           'title':'A PR','body':'Updated','html_url':pull['url'],'comments_url':'https://api.github.com/repos/o/r/issues/2/comments'})
        if req.url.path=='/repos/o/r/pulls/2':return httpx.Response(200,json={'merged':True})
        if req.url.path.endswith(('/comments','/reviews')):
            requests.append(req);return httpx.Response(200,json=[])
        return original.handle_request(req)
    rows,coverage=GitHub(httpx.Client(transport=httpx.MockTransport(handle))).repo('o/r',previous)
    assert any(r.url.path=='/repos/o/r/pulls/2/reviews' for r in requests)
    assert not any(r['id']==thread['id'] for r in rows)
    assert next(r for r in rows if r['id']==pull['id'])['lifecycle']=='merged'
    assert coverage['state']=='partial'  # GraphQL credential boundary remains explicit.


def test_old_closed_pr_waits_for_weekly_reconciliation():
    previous=baseline()
    pull=record('github:P3','old','https://github.com/o/r/pull/3','Old PR','o/r','pull',lifecycle='merged',updated='2025-01-01T00:00:00Z',permissions='full-text')
    previous['records'].append(pull)
    client,requests=changed_client(issue_rows=[])
    rows,coverage=GitHub(client).repo('o/r',previous)
    assert coverage['poll_mode']=='overlap'
    assert not any(r.url.path.endswith('/issues/3') for r in requests)
    assert next(r for r in rows if r['id']==pull['id'])==pull


def test_operator_reuse_approval_overrides_licence(tmp_path):
    from gateway.ingest import reuse_policy
    cfg=tmp_path/'sources.json'
    cfg.write_text(json.dumps({'organization':'o','repositories':['r'],'initial':['r'],'allowed_reference_hosts':[],
                              'reuse_permissions':{'default':'metadata-only','overrides':{'o/r':'full-text'}}}))
    assert reuse_policy({},'o/r') is None
    with pytest.raises(ValueError):reuse_policy({'reuse_permissions':{'default':'everything'}},'o/r')
    client,_=fixture_api()
    rows,manifest=capture(cfg,tmp_path/'owned',client=client)
    entry=manifest['coverage'][0]
    assert entry['reuse_basis']=='operator-approval' and entry['reuse_permissions']=='full-text'
    assert all(r['reuse_permissions']=='full-text' for r in rows if r['kind'] in ('issue','comment','file'))
