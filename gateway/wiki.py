import subprocess,tempfile,os
from pathlib import Path
from .model import record

def capture(repo,permission):
    # Git transport fetch only; local bare copy in temporary project-owned storage.
    with tempfile.TemporaryDirectory(prefix='knowledge-wiki-') as directory:
        result=subprocess.run(['git','clone','--bare','https://github.com/'+repo+'.wiki.git',directory],capture_output=True,text=True,timeout=120,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
        if result.returncode:
            if any(term in result.stderr.lower() for term in ['not found','could not read username','terminal prompts disabled']):return [],'not-present-or-unavailable'
            raise RuntimeError('Wiki fetch failed: '+result.stderr[:300])
        def git(*args):return subprocess.check_output(['git','--git-dir',directory,*args],text=True,timeout=60)
        revision=git('rev-parse','HEAD').strip();rows=[]
        for path in git('ls-tree','-r','--name-only','HEAD').splitlines():
            if path.endswith(('.md','.rst','.txt')):
                text=git('show',revision+':'+path)
                rows.append(record('wiki:'+repo+':'+path,revision,'https://github.com/'+repo+'/wiki/'+Path(path).stem,text,repo,'wiki',path=path,permissions=permission))
        return rows,'complete-supported-text'
