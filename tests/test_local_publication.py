"""Filesystem publication regressions; no live database or source credentials."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'publish_local.py'


class LocalPublicationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'Local publication adapter is missing')
        spec = importlib.util.spec_from_file_location('publish_local', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.staged = self.root / 'staged'
        self.staged.mkdir()
        self.snapshot = 'a' * 24
        self.publication = {'snapshot': self.snapshot, 'capture_complete': True, 'safety_withdrawal': False}
        (self.staged / '.knowledge-generated').write_text('owned')
        for filename, data in [('config.json', {'snapshot': self.snapshot}),
                               ('manifest.json', {'snapshot': self.snapshot}),
                               ('verification.json', {'snapshot': self.snapshot, 'navigation_valid': True, 'permissions_valid': True})]:
            (self.staged / filename).write_text(json.dumps(data))
        (self.staged / 'index.html').write_text('new release')
        self.events = []

    def old_release(self):
        old = self.root / 'releases' / ('b' * 24)
        old.mkdir(parents=True)
        (old / 'index.html').write_text('previous release')
        (self.root / 'current').symlink_to(old.relative_to(self.root), target_is_directory=True)
        return old

    def activate(self, verify=None, promote=None, can_restore=None):
        return self.module.activate_site(self.staged, self.root, self.publication,
                                        verify or (lambda sid: self.events.append('verified')),
                                        promote or (lambda sid: self.events.append('promoted')),
                                        can_restore=can_restore)

    def test_site_is_installed_and_verified_before_api_promotion(self):
        def verify(sid):
            self.assertEqual(sid, self.snapshot)
            self.assertEqual((self.root / 'current' / 'index.html').read_text(), 'new release')
            self.events.append('verified')
        self.activate(verify=verify)
        self.assertEqual(self.events, ['verified', 'promoted'])

    def test_partial_capture_cannot_replace_previous_release(self):
        old = self.old_release()
        self.publication['capture_complete'] = False
        with self.assertRaises(ValueError):
            self.activate()
        self.assertEqual((self.root / 'current').resolve(), old)
        self.assertEqual(self.events, [])

    def test_failed_https_check_restores_previous_site_without_promoting(self):
        old = self.old_release()
        def fail(sid):
            raise RuntimeError('HTTPS failed')
        with self.assertRaises(RuntimeError):
            self.activate(verify=fail)
        self.assertEqual((self.root / 'current').resolve(), old)
        self.assertEqual(self.events, [])

    def test_failed_promotion_restores_previous_site(self):
        old = self.old_release()
        def fail(sid):
            raise RuntimeError('DB promotion failed')
        with self.assertRaises(RuntimeError):
            self.activate(promote=fail)
        self.assertEqual((self.root / 'current').resolve(), old)

    def test_failed_first_publication_removes_current_link(self):
        def fail(sid):
            raise RuntimeError('HTTPS failed')
        with self.assertRaises(RuntimeError):
            self.activate(verify=fail)
        self.assertFalse((self.root / 'current').is_symlink())

    def test_mismatched_generated_snapshot_is_refused(self):
        (self.staged / 'manifest.json').write_text(json.dumps({'snapshot': 'b' * 24}))
        with self.assertRaises(ValueError):
            self.activate()
        self.assertEqual(self.events, [])

    def test_snapshot_cannot_escape_release_directory(self):
        self.publication['snapshot'] = '../outside'
        with self.assertRaises(ValueError):
            self.activate()

    def test_release_is_readable_by_the_separate_unprivileged_web_container(self):
        self.staged.chmod(0o700)
        (self.staged / 'index.html').chmod(0o600)
        self.activate()
        release = (self.root / 'current').resolve()
        self.assertEqual(release.stat().st_mode & 0o777, 0o755)
        self.assertEqual((release / 'index.html').stat().st_mode & 0o777, 0o644)

    def test_retry_refuses_an_altered_existing_release(self):
        self.activate()
        (self.root / 'current' / 'index.html').write_text('altered')
        with self.assertRaises(ValueError):
            self.activate()

    def test_incomplete_capture_cannot_claim_an_unevidenced_withdrawal(self):
        self.publication.update(capture_complete=False, safety_withdrawal=True)
        with self.assertRaises(ValueError):
            self.activate()
        self.assertEqual(self.events, [])

    def test_unknown_current_directory_is_preserved(self):
        (self.root / 'current').mkdir()
        (self.root / 'current' / 'unowned.txt').write_text('preserve')
        with self.assertRaises(ValueError):
            self.activate()
        self.assertTrue((self.root / 'current' / 'unowned.txt').exists())

    def test_reconciliation_failure_does_not_restore_a_revoked_export(self):
        old = self.old_release()
        (old / 'sources.jsonl').write_text(json.dumps({'id': 'removed', 'url': 'https://example.org/removed'}))
        def fail(sid):
            raise RuntimeError('HTTPS failed')
        with self.assertRaises(RuntimeError):
            self.activate(verify=fail, can_restore=lambda path: self.module.site_is_safe(path, ['removed']))
        self.assertNotEqual((self.root / 'current').resolve(), old)

    def test_failed_generation_hides_a_previously_served_withdrawn_source(self):
        old = self.old_release()
        (old / 'sources.jsonl').write_text(json.dumps({'id': 'removed', 'url': 'https://example.org/removed'}))
        with self.assertRaises(RuntimeError):
            with self.module.publication_guard(self.root, lambda: ['removed']):
                raise RuntimeError('Generation failed after DB revocation')
        self.assertFalse((self.root / 'current').is_symlink())

    def test_unrelated_capture_failure_preserves_a_safe_previous_site(self):
        old = self.old_release()
        (old / 'sources.jsonl').write_text(json.dumps({'id': 'retained', 'url': 'https://example.org/retained'}))
        with self.assertRaises(RuntimeError):
            with self.module.publication_guard(self.root, lambda: ['removed']):
                raise RuntimeError('Capture failed')
        self.assertEqual((self.root / 'current').resolve(), old)

    def test_emergency_withdrawal_never_restores_the_unsafe_previous_site(self):
        old = self.old_release()
        self.publication.update(capture_complete=False, safety_withdrawal=True)
        (self.staged / 'manifest.json').write_text(json.dumps({'snapshot': self.snapshot, 'coverage': {'withdrawal': {'repositories': ['withdrawn']}}}))
        def fail(sid):
            raise RuntimeError('HTTPS failed')
        with self.assertRaises(RuntimeError):
            self.activate(verify=fail)
        self.assertNotEqual((self.root / 'current').resolve(), old)


if __name__ == '__main__':
    unittest.main()
