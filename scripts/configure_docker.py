"""Create a private, local Compose env file without printing credentials."""
import argparse
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='Public DNS hostname, without scheme')
    parser.add_argument('--output', default='.env')
    args = parser.parse_args()
    host = args.host
    parsed = urlsplit('https://' + host)
    if (not host.isascii() or not parsed.hostname or parsed.netloc != host
            or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for c in host)
            or len(host) > 253 or any(not label or len(label) > 63 or label.startswith('-') or label.endswith('-') for label in host.split('.'))):
        parser.error('--host must be a DNS hostname without a scheme, port or path')
    target = Path(args.output)
    # Exclusive creation prevents accidental password rotation on an existing DB.
    admin, reader, writer = (secrets.token_hex(32) for _ in range(3))
    data = {
        'DATABASE_ADMIN_PASSWORD': admin,
        'ADMIN_DATABASE_URL': f'postgresql://postgres:{admin}@db:5432/knowledge',
        'READER_DATABASE_PASSWORD': reader,
        'INGEST_DATABASE_PASSWORD': writer,
        'RETRIEVAL_DATABASE_URL': f'postgresql://gateway_reader:{reader}@db:5432/knowledge',
        'INGEST_DATABASE_URL': f'postgresql://gateway_ingest:{writer}@db:5432/knowledge',
        'SERVICE_HOST': host,
        'PUBLIC_API_URL': 'https://' + host,
        'ALLOWED_ORIGINS': 'https://nklomp.github.io,https://' + host,
        'SOURCE_READ_TOKEN': '',
    }
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.error(f'{target} already exists; preserving existing credentials')
    with os.fdopen(fd, 'w') as out:
        out.write('# Local Docker settings; never commit or share this file.\n')
        out.writelines(f'{key}={value}\n' for key, value in data.items())
    print(f'Created {target} with mode 0600. Credentials were not printed.')
    print('Bind a dedicated read-only SOURCE_READ_TOKEN before complete ingestion.')


if __name__ == '__main__':
    main()
