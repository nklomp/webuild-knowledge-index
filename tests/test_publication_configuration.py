import base64
from types import SimpleNamespace
import pytest
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('configure_publication',Path(__file__).parents[1]/'scripts/configure_publication.py')
config=importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def test_inspection_distinguishes_permission_from_missing_pages(monkeypatch):
    monkeypatch.setattr(config,'api',lambda *a:SimpleNamespace(returncode=1,stdout='{"status":"403"}',stderr='See documentation: 404'))
    assert config.inspection()['pages']=='permission-denied'


def test_bad_checkpoint_key_stops_before_any_network_or_mutation(monkeypatch):
    monkeypatch.setenv('CHECKPOINT_KEY',base64.b64encode(b'too short').decode())
    monkeypatch.setattr(config,'api',lambda *a:pytest.fail('must validate before writes'))
    with pytest.raises(ValueError,match='32 random bytes'):config.apply({'can_apply':True})


def test_secret_value_uses_stdin_and_separate_admin_identity(monkeypatch):
    monkeypatch.setenv('GATEWAY_ADMIN_TOKEN','admin-sentinel')
    monkeypatch.setenv('SOURCE_READ_TOKEN','source-sentinel')
    seen=[]
    monkeypatch.setattr(config.subprocess,'run',lambda argv,**kwargs:seen.append((argv,kwargs)))
    config.gh('secret','set','SOURCE_READ_TOKEN',data='source-sentinel')
    argv,options=seen[0]
    assert 'source-sentinel' not in argv and 'admin-sentinel' not in argv
    assert options['input']=='source-sentinel'
    assert options['env']['GH_TOKEN']=='admin-sentinel'
