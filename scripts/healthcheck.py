"""Run from an independent monitor, never from the gateway website.
No notification is sent by default. Wire an already authorized operator channel externally.
"""
import os,sys,httpx
try:
    r=httpx.get(os.environ['PUBLIC_API_URL'].rstrip('/')+'/health',timeout=10);r.raise_for_status()
    report=r.json()
    if report.get('failed_sources'):raise RuntimeError('Source capture failure: '+str(report['failed_sources']))
    print(report)
except Exception as e:
    print('FRESHNESS/AVAILABILITY FAILURE: '+str(e),file=sys.stderr);sys.exit(1)
