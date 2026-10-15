import importlib.util,io,json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('healthcheck',Path('scripts/healthcheck.py'))
health=importlib.util.module_from_spec(spec);spec.loader.exec_module(health)

class Endpoint:
    def __init__(self,report):self.report=report
    def open(self,url,timeout):
        assert url=='https://api.example.org/health' and timeout==10
        return io.BytesIO(json.dumps(self.report).encode())

def report():return {'snapshot':'published','age_seconds':120,'freshness_failure':False,'failed_sources':[],'stale_sources':[]}

def test_monitor_uses_public_endpoint_without_database_or_source_credentials():
    assert health.check('https://api.example.org',Endpoint(report()))['healthy']

@pytest.mark.parametrize('change',[{'age_seconds':129601},{'age_seconds':float('nan')},{'freshness_failure':True},{'failed_sources':['failed']},{'stale_sources':['stale']},{'snapshot':''}])
def test_successful_http_with_unhealthy_payload_is_failure(change):
    with pytest.raises(ValueError):health.check('https://api.example.org',Endpoint(report()|change))

@pytest.mark.parametrize('url',['http://public.example.org','https://secret:password@example.org','https://example.org/?token=secret'])
def test_monitor_rejects_plaintext_and_credentials_in_public_url(url):
    with pytest.raises(ValueError):health.check(url)
