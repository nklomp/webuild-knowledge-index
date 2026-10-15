"""Prepare and publish the local wiki before promoting its matching API snapshot."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


def site_is_safe(directory, withdrawals):
    revoked = set(withdrawals)
    if not revoked:
        return True
    try:
        with (Path(directory) / 'sources.jsonl').open() as stream:
            for line in stream:
                record = json.loads(line)
                if record['id'] in revoked or record['url'] in revoked:
                    return False
        return True
    except (OSError, ValueError, KeyError):
        return False


@contextmanager
def publication_guard(root, withdrawals):
    try:
        yield
    except BaseException:
        current = Path(root) / 'current'
        if current.is_symlink():
            try:
                safe = site_is_safe(current, withdrawals())
            except Exception:
                safe = False
            if not safe:
                # Generation can fail after preparation revokes old records.
                # Unavailable static hosting is safer than serving withdrawn data.
                current.unlink()
        raise


def activate_site(staged, root, publication, verify_public, promote, can_restore=None):
    staged, root = Path(staged).resolve(), Path(root).resolve()
    sid = publication.get('snapshot', '')
    if not re.fullmatch(r'[0-9a-f]{24}', sid):
        raise ValueError('Invalid snapshot identity')
    if not staged.is_relative_to(root) or staged == root:
        raise ValueError('Staging must be inside the owned site volume')
    if not (staged / '.knowledge-generated').is_file():
        raise ValueError('Staging is not an owned generated site')
    manifest = json.loads((staged / 'manifest.json').read_text())
    verification = json.loads((staged / 'verification.json').read_text())
    config = json.loads((staged / 'config.json').read_text())
    if any(data.get('snapshot') != sid for data in [manifest, verification, config]):
        raise ValueError('Generated site and prepared snapshot differ')
    if not verification.get('navigation_valid') or not verification.get('permissions_valid'):
        raise ValueError('Generated site verification failed')
    safety = publication.get('safety_withdrawal') is True
    if safety:
        if not manifest.get('coverage', {}).get('withdrawal'):
            raise ValueError('Safety publication lacks withdrawal evidence')
    elif publication.get('capture_complete') is not True:
        raise ValueError('Incomplete capture cannot be published')
    current = root / 'current'
    if current.exists() and not current.is_symlink():
        raise ValueError('Refusing to replace an unowned current directory')
    previous = os.readlink(current) if current.is_symlink() else None
    if previous and not current.resolve().is_relative_to(root / 'releases'):
        raise ValueError('Previous site points outside the release directory')
    releases = root / 'releases'
    releases.mkdir(exist_ok=True)
    release = releases / sid
    if release.exists():
        # A retry must never reuse an altered or partial release.
        expected = {p.relative_to(staged): p for p in staged.rglob('*') if p.is_file()}
        actual = {p.relative_to(release): p for p in release.rglob('*') if p.is_file()}
        if expected.keys() != actual.keys() or any(expected[k].read_bytes() != actual[k].read_bytes() for k in expected):
            raise ValueError('Existing release differs from generated site')
    else:
        temporary = releases / ('.build-' + uuid.uuid4().hex)
        shutil.copytree(staged, temporary)
        # The generator uses mkdtemp (0700). Nginx has a different Unix UID.
        temporary.chmod(0o755)
        for path in temporary.rglob('*'):
            path.chmod(0o755 if path.is_dir() else 0o644)
        temporary.rename(release)
    pending = root / ('.current-' + uuid.uuid4().hex)
    pending.symlink_to(release.relative_to(root), target_is_directory=True)
    os.replace(pending, current)
    try:
        verify_public(sid)
        promote(sid)
    except BaseException:
        # A safety site must never roll back to known withdrawn material.
        if not safety and (not previous or can_restore is None or can_restore(root / previous)):
            if previous:
                pending.symlink_to(previous, target_is_directory=True)
                os.replace(pending, current)
            else:
                current.unlink()
        raise
    return sid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-only', action='store_true')
    args = parser.parse_args()
    import fcntl
    import httpx
    from gateway.embeddings import Embeddings
    from gateway.site import verify_site
    from gateway.store import Store
    artifacts, root = Path('/app/artifacts'), Path('/app/site')
    # The volume root is a mount point and cannot be renamed by the generator.
    staged = root / 'staged'
    artifacts.mkdir(exist_ok=True)
    store = Store(os.environ['INGEST_DATABASE_URL'], Embeddings())
    with (artifacts / 'local-publication.lock').open('a') as lock, publication_guard(root, store.withdrawals):
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not args.prepared_only:
            subprocess.run([sys.executable, '-m', 'gateway.cli', 'run', '--site', str(staged)], check=True)
        publication = json.loads((artifacts / 'publication.json').read_text())
        sid = publication['snapshot']
        manifest = store.manifest(sid)
        if not publication.get('safety_withdrawal'):
            coverage = manifest['coverage']
            if coverage.get('status') != 'complete' or any(e['state'] in ['failed', 'partial'] for e in coverage['coverage']):
                raise ValueError('Database snapshot lacks complete capture coverage')
        verify_site(staged, manifest)
        if not site_is_safe(staged, store.withdrawals()):
            raise ValueError('Prepared site contains revoked sources')
        base = os.environ['PUBLIC_API_URL'].rstrip('/')
        def verify_public(snapshot):
            with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
                for path in ['/manifest.json', '/config.json', '/v1/manifest?snapshot=' + snapshot]:
                    response = client.get(base + path)
                    response.raise_for_status()
                    if response.status_code != 200 or response.json().get('snapshot') != snapshot:
                        raise ValueError('Public wiki/API snapshot verification failed')
                response = client.get(base + '/')
                if response.status_code != 200 or snapshot not in response.text:
                    raise ValueError('Public wiki did not serve the selected snapshot')
        activate_site(staged, root, publication, verify_public, store.promote,
                      can_restore=lambda directory: site_is_safe(directory, store.withdrawals()))
        print(json.dumps({'published': True, 'snapshot': sid, 'site': base,
                          'safety_withdrawal': publication.get('safety_withdrawal', False)}))


if __name__ == '__main__':
    main()
