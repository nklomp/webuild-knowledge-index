"""Human-facing labels, titles and grouping for the generated wiki. Presentation only: never changes records."""
import re
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import urlparse, unquote

OWNERS = {
    'webuild-consortium': ('WE BUILD consortium', 'Working groups and shared repositories of the WE BUILD large scale pilot.'),
    'eu-digital-identity-wallet': ('EU Digital Identity Wallet', 'Upstream EUDI Wallet architecture and specification repositories.'),
    'external-specifications': ('Referenced specifications', 'Standards, regulations and specifications cited by the sources.'),
}
REPOSITORIES = {
    'wp4-architecture': ('Architecture', 'Architecture decision records, the blueprint and conformance specifications.'),
    'wp4-trust-group': ('Trust group', 'Trust framework, onboarding, certificate profiles, trust evaluation and ETSI reference material.'),
    'wp4-semantics-group': ('Semantics group', 'European Business Wallet Vocabulary (EBWV), semantic intakes, ontology and application profiles.'),
    'webuild-attestation-rulebooks-catalog': ('Attestation rulebooks catalogue', 'Attestation rulebooks, schemas and samples.'),
    'wp4-qtsp-group': ('QTSP group', None),
    'wp4-wallets-group': ('Wallets group', None),
    'wp4-pid-ebwoid-group': ('PID / EBWOID group', None),
    'wp4-interop-test-bed': ('Interoperability test bed', None),
    'webuild-github-policies': ('GitHub policies', None),
    '.github': ('Consortium profile', None),
    'eudi-doc-architecture-and-reference-framework': ('Architecture and Reference Framework (ARF)', 'The EUDI Wallet Architecture and Reference Framework, its annexes and discussions.'),
    'eudi-doc-standards-and-technical-specifications': ('Standards and technical specifications', 'EUDI Wallet standards and technical specification documents.'),
    'external-specifications': ('Referenced specifications', 'Standards, regulations and specifications cited by the indexed sources.'),
}
TOPICS = {
    'AuthZEN': 'OpenID AuthZEN authorization API, including EAA key-binding checks.',
    'EBWV': 'European Business Wallet Vocabulary: shared business terminology and identifiers.',
    'OID4VP': 'OpenID for Verifiable Presentations: presenting credentials from a wallet.',
    'OID4VCI': 'OpenID for Verifiable Credential Issuance: issuing credentials into a wallet.',
    'trust': 'Trust frameworks, trusted lists, certificates and trust evaluation.',
    'rulebook': 'Attestation rulebooks describing credential types and their rules.',
}
# Category order is the browsing order: decisions and requirements before documents, conversations after.
CATEGORIES = [
    ('decisions', 'Decisions', 'Architecture decision records (ADRs).'),
    ('conformance', 'Conformance specifications', 'Implementation requirements.'),
    ('documents', 'Documents', 'Markdown, text and PDF documents.'),
    ('specifications', 'Specifications', 'Official and referenced external specifications.'),
    ('discussions', 'Discussions', 'GitHub discussions.'),
    ('issues', 'Issues', 'Reported issues and concerns.'),
    ('pulls', 'Pull requests', 'Proposed changes.'),
    ('releases', 'Releases', 'Published releases and their attachments.'),
    ('files', 'Other files', 'Images, archives and other files without extracted text.'),
    ('replies', 'Comments and reviews', 'Contributions inside discussions, issues and pull requests.'),
]
CATEGORY_LABELS = {key: label for key, label, _ in CATEGORIES}
KIND_LABELS = {
    'file': 'Document', 'wiki': 'Wiki page', 'pdf': 'PDF document', 'binary-metadata': 'File',
    'issue': 'Issue', 'pull': 'Pull request', 'discussion': 'Discussion', 'comment': 'Comment',
    'discussion-comment': 'Discussion comment', 'discussion-reply': 'Discussion reply',
    'reviews': 'Review', 'review_comments': 'Review comment', 'review-thread': 'Review thread',
    'release': 'Release', 'attachment-metadata': 'Release attachment',
    'external-reference': 'Referenced specification', 'official-specification': 'Official specification',
}
REPLY_KINDS = {'comment', 'discussion-comment', 'discussion-reply', 'reviews', 'review_comments', 'review-thread'}
STATES = {'open': 'Open', 'closed': 'Closed', 'merged': 'Merged', 'resolved': 'Resolved', 'unresolved': 'Unresolved',
          'APPROVED': 'Approved', 'COMMENTED': 'Commented', 'CHANGES_REQUESTED': 'Changes requested', 'DISMISSED': 'Dismissed'}
THREAD_RE = re.compile(r'^https://github\.com/([^/]+/[^/]+)/(issues|pull|discussions)/(\d+)')
TITLE_SUFFIX = re.compile(r'\s*\((?:review_comments|reviews|comment|reply|discussion comment)\)\s*$')
HOSTS = {'eur-lex.europa.eu': 'EUR-Lex', 'www.etsi.org': 'ETSI', 'etsi.org': 'ETSI', 'forge.etsi.org': 'ETSI Forge',
         'openid.net': 'OpenID', 'www.rfc-editor.org': 'RFC Editor', 'datatracker.ietf.org': 'IETF', 'www.ietf.org': 'IETF',
         'www.w3.org': 'W3C', 'github.com': 'GitHub'}
CODE_EXTENSIONS = {'.json', '.jsonld', '.yaml', '.yml', '.ttl', '.xml', '.xsd', '.csv', '.rdf', '.owl', '.shacl', '.py', '.js', '.ts', '.sh'}


def owner_of(repository):
    return repository.split('/', 1)[0] if '/' in repository else repository


def owner_label(repository):
    owner = owner_of(repository)
    return OWNERS.get(owner, (owner, None))[0]


def repository_label(repository):
    name = repository.rsplit('/', 1)[-1]
    if name in REPOSITORIES: return REPOSITORIES[name][0]
    words = name.replace('-', ' ').replace('_', ' ').strip('. ')
    return words if words.isupper() else words.capitalize()


def repository_description(repository):
    name = repository.rsplit('/', 1)[-1]
    return REPOSITORIES.get(name, (None, None))[1]


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-') or 'item'


def category(r):
    kind = r['kind']
    if kind in REPLY_KINDS: return 'replies'
    if r.get('role') == 'decision': return 'decisions'
    if r.get('role') == 'implementation-requirement': return 'conformance'
    if kind in ('file', 'wiki', 'pdf'): return 'documents'
    if kind in ('external-reference', 'official-specification'): return 'specifications'
    if kind == 'discussion': return 'discussions'
    if kind == 'issue': return 'issues'
    if kind == 'pull': return 'pulls'
    if kind in ('release', 'attachment-metadata'): return 'releases'
    return 'files'


def kind_label(r):
    if r.get('role') == 'decision': return 'Decision record'
    if r.get('role') == 'implementation-requirement': return 'Conformance specification'
    return KIND_LABELS.get(r['kind'], r['kind'].replace('-', ' ').replace('_', ' ').capitalize())


def state_label(r):
    return STATES.get(r.get('lifecycle'))


def thread_key(url):
    """Canonical URL of the issue, pull request or discussion a GitHub URL belongs to."""
    match = THREAD_RE.match(url or '')
    return 'https://github.com/%s/%s/%s' % match.groups() if match else None


def thread_number(url):
    match = THREAD_RE.match(url or '')
    return int(match.group(3)) if match else None


def friendly_date(value):
    if not value: return ''
    try: day = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError: return value[:10]
    return '%d %s' % (day.day, day.strftime('%b %Y'))


def iso_day(value):
    return (value or '')[:10]


def _first_heading(text):
    fenced = False
    for line in text.splitlines()[:80]:
        if line.lstrip().startswith('```'): fenced = not fenced; continue
        if fenced: continue
        match = re.match(r'^#\s+(.+?)\s*#*\s*$', line)
        if match:
            title = re.sub(r'<[^>]+>|[*_`]|\[([^\]]*)\]\([^)]*\)', lambda m: m.group(1) or '', match.group(1)).strip()
            if title: return title[:160]
    return None


def _humanise_file(path):
    p = PurePosixPath(path)
    if p.stem.lower() in ('readme', 'index'):
        return (p.parent.name.replace('-', ' ').replace('_', ' ').capitalize() + ' overview') if p.parent.name else 'Repository overview'
    if p.suffix.lower() in ('.md', '.markdown', '.rst', '.txt'):
        words = p.stem.replace('-', ' ').replace('_', ' ').strip()
        return words[:1].upper() + words[1:]
    return p.name


def _reference_title(url):
    u = urlparse(url); host = u.hostname or ''; path = unquote(u.path)
    if 'rfc-editor.org' in host or 'ietf.org' in host:
        rfc = re.search(r'rfc(\d{3,5})', path, re.I)
        if rfc: return 'RFC ' + rfc.group(1)
        draft = re.search(r'(draft-[a-z0-9-]+)', path, re.I)
        if draft: return draft.group(1)
    if 'etsi.org' in host:
        etsi = re.search(r'(ts|en|tr|es)_?(\d{3})(\d{3})(\d{2})?v(\d{2})(\d{2})(\d{2})', path, re.I)
        if etsi:
            kind, a, b, part, x, y, z = etsi.groups()
            return 'ETSI %s %s %s%s V%d.%d.%d' % (kind.upper(), a, b, '-' + str(int(part)) if part and int(part) else '', int(x), int(y), int(z))
    if 'eur-lex' in host:
        celex = re.search(r'CELEX[:%3A]+3(\d{4})([RLD])(\d{4})', url, re.I)
        if celex:
            year, kind, number = celex.groups()
            return '%s (EU) %s/%d' % ({'R': 'Regulation', 'L': 'Directive', 'D': 'Decision'}[kind.upper()], year, int(number))
        eli = re.search(r'/eli/(reg_impl|reg_del|reg|dir_impl|dir|dec_impl|dec_del|dec)/(\d{4})/(\d+)', path)
        if eli:
            kind = {'reg': 'Regulation', 'reg_impl': 'Implementing Regulation', 'reg_del': 'Delegated Regulation', 'dir': 'Directive',
                    'dir_impl': 'Implementing Directive', 'dec': 'Decision', 'dec_impl': 'Implementing Decision', 'dec_del': 'Delegated Decision'}[eli.group(1)]
            return '%s (EU) %s/%s' % (kind, eli.group(2), eli.group(3))
    segments = [s for s in path.split('/') if s and s.lower() not in ('oj', 'eng', 'en', 'tr', 'specs', 'doc', 'html', 'deliver', '-', 'raw', 'blob')]
    tail = '/'.join(segments[-2:]) if segments else ''
    tail = re.sub(r'\.(html?|pdf)$', '', tail)
    label = HOSTS.get(host, host.removeprefix('www.'))
    return label + (' — ' + tail if tail else '')


def display_title(r):
    title = (r.get('title') or '').strip()
    raw = not title or title == r['id'] or re.match(r'^(external|official|github):', title)
    if r['kind'] in ('file', 'wiki'):
        heading = _first_heading(r.get('text') or '') if (r.get('locator', '').lower().endswith(('.md', '.markdown')) or r['kind'] == 'wiki') else None
        return heading or _humanise_file(r.get('locator') or title)
    if r['kind'] in ('pdf', 'binary-metadata'):
        return PurePosixPath(r.get('locator') or title).name
    if r['kind'] in ('external-reference',) or (raw and r['kind'] == 'official-specification'):
        return _reference_title(r['url'])
    if raw and r['kind'] in ('discussion', 'issue', 'pull'):
        number = thread_number(r['url'])
        return '%s #%s' % (KIND_LABELS[r['kind']], number) if number else KIND_LABELS[r['kind']]
    if raw:
        return _reference_title(r['url'])
    return TITLE_SUFFIX.sub('', title)


def subtitle(r):
    """Short secondary locator shown next to a title: a path or a thread number."""
    if r['kind'] in ('file', 'wiki', 'pdf', 'binary-metadata'): return r.get('locator') or ''
    number = thread_number(r['url'])
    if number and r['kind'] in ('issue', 'pull', 'discussion'): return '#%d' % number
    if r['kind'] in ('external-reference', 'official-specification'): return urlparse(r['url']).hostname or ''
    return ''


def content_format(r):
    locator = (r.get('locator') or '').lower()
    if r['kind'] == 'pdf' or '<!-- page 1 -->' in (r.get('text') or '')[:200]: return 'pdf'
    if PurePosixPath(locator).suffix in CODE_EXTENSIONS: return 'code'
    if r['kind'] in ('official-specification',) and not locator.endswith(('.md', '.html', '.htm')): return 'plain'
    return 'markdown'
