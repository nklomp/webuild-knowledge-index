"""Regenerate recovery block 119's descriptive fixtures from checked public evidence.

Run with `uv run --frozen python -m scripts.regenerate_source_evidence`.
No recorded shell commands are executed. Issue bodies have no immutable Git URL:
both their observed update timestamp and content hash must match the pin below.
An edited upstream issue fails closed and requires a reviewed new pin.
"""
import argparse
import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from gateway.ingest import atomic_json
from gateway.model import digest, now

COMMIT = 'a78fb62ef8cd037b5038ef1418bb26f1d902995e'
PATH = 'adr/eaa-key-binding-authzen.md'
AUTHZEN_HASH = '1ec024467449cd4a04ff2bf21969adab8b6a485262773f462f65f856e1323a64'
ISSUE_URL = 'https://github.com/webuild-consortium/wp4-trust-group/issues/104'
ISSUE_UPDATED = '2026-09-30T14:38:13Z'
ISSUE_HASH = 'cfa1968ebbb129115991dd22d83e7175885dae8501cd59e346525bca364491c4'


def issue_from_html(html):
    for script in BeautifulSoup(html, 'html.parser').find_all('script', type='application/json'):
        try:
            issue = json.loads(script.text)['payload']['issueViewerRoute']['data']['repository']['issue']
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        if issue['url'] == ISSUE_URL and issue['repository']['visibility'] == 'PUBLIC' and not issue['repository']['isPrivate']:
            return issue
    raise ValueError('Expected public authoritative issue payload unavailable')


def proofs_from_sources(authzen, issue):
    issue_text = issue['title'] + '\n' + issue['body']
    if digest(authzen) != AUTHZEN_HASH:
        raise ValueError('Pinned AuthZEN content hash mismatch')
    if issue['updatedAt'] != ISSUE_UPDATED or digest(issue_text) != ISSUE_HASH:
        raise ValueError('Pinned issue revision/content changed; review new evidence explicitly')
    proofs = [
        {'id': 'authzen-archival', 'url': f'https://github.com/webuild-consortium/wp4-architecture/blob/{COMMIT}/{PATH}',
         'content_hash': AUTHZEN_HASH, 'source_revision': COMMIT, 'expected_kind': 'file', 'expected_status': 'unknown',
         'source_excerpt': 'the archival case remains open',
         'attribution': 'The AuthZEN ADR leaves historical key-binding queries open pending an extension of the cited draft.'},
        {'id': 'etsi-104', 'url': ISSUE_URL, 'content_hash': ISSUE_HASH, 'source_revision': ISSUE_UPDATED,
         'expected_kind': 'issue', 'expected_status': 'unknown', 'source_excerpt': 'ETSI TS 119 602 V1.1.1 (2025-11)',
         'attribution': 'Issue 104 reports differences between the ETSI JSON schema and PDF. This is a reported concern, not an official correction.',
         'official_schema_revision': 'e84f427f0cde99513b574ef4b5a155ac4a38eab6',
         'clause_identifiers': ['6.3.3', '6.3.5', '6.3.7', '6.3.8', '6.3.9', '6.3.10', '6.3.11']},
    ]
    for proof, text in zip(proofs, [authzen, issue_text]):
        if proof['source_excerpt'] not in text:
            raise ValueError('Descriptive note lacks exact source evidence')
        proof['evidence_label'] = 'source-derived; not a participant question'
    return proofs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authzen-file', type=Path)
    parser.add_argument('--issue-html', type=Path)
    args = parser.parse_args()
    with httpx.Client(timeout=60, follow_redirects=False) as client:
        def read(url):
            response = client.get(url)
            response.raise_for_status()
            return response.text
        authzen = args.authzen_file.read_text() if args.authzen_file else read(f'https://raw.githubusercontent.com/webuild-consortium/wp4-architecture/{COMMIT}/{PATH}')
        html = args.issue_html.read_text() if args.issue_html else read(ISSUE_URL)
    proofs = proofs_from_sources(authzen, issue_from_html(html))
    for path in ['config/source-evidence.json', 'tests/fixtures/source-evidence.json']:
        atomic_json(path, proofs)
    atomic_json('evidence/source-fixture-regeneration.json', {
        'regenerated_at': now(), 'recovery_reference': 'recorded-source-writes block 119',
        'sources': proofs, 'checks': ['public issue visibility', 'exact content hashes', 'issue update revision', 'immutable file commit', 'exact excerpts'],
        'limits': 'Fresh public reads, not recovered historical artifacts. ETSI schema revision is the issue citation; schema/PDF claims are attributed to the issue, not independently established.'})
    print('Regenerated two checked source-derived fixtures; upstream sources unchanged.')


if __name__ == '__main__':
    main()
