"""Authenticate and encrypt ingestion journals before placing them in any public CI cache."""
import argparse,base64,io,os,tarfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
AAD=b'webuild-knowledge-index/checkpoint-v1'
def key():
    value=base64.b64decode(os.environ['CHECKPOINT_KEY'],validate=True)
    if len(value)!=32:raise ValueError('CHECKPOINT_KEY must contain 32 random bytes encoded as base64')
    return value

def seal(root,output):
    root=Path(root);payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w:gz') as tar:
        for name in ['capture-state.json','captures']:
            path=root/name
            if path.exists():tar.add(path,arcname=name,recursive=True)
    nonce=os.urandom(12);Path(output).write_bytes(b'WBKI1'+nonce+AESGCM(key()).encrypt(nonce,payload.getvalue(),AAD))

def restore(input,root):
    blob=Path(input).read_bytes()
    if blob[:5]!=b'WBKI1':raise ValueError('Unknown checkpoint format')
    plain=AESGCM(key()).decrypt(blob[5:17],blob[17:],AAD);root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(plain),mode='r:gz') as tar:
        for member in tar.getmembers():
            target=(root/member.name).resolve()
            if not target.is_relative_to(root) or not (member.isfile() or member.isdir()):raise ValueError('Invalid checkpoint member')
        tar.extractall(root,filter='data')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['seal','restore']);p.add_argument('--root',default='artifacts');p.add_argument('--sealed',default='checkpoint-cache/sealed.bin');a=p.parse_args()
    Path(a.sealed).parent.mkdir(parents=True,exist_ok=True)
    if a.command=='seal':seal(a.root,a.sealed)
    else:restore(a.sealed,a.root)
