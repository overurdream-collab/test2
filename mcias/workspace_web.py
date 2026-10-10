"""Explicit frontend routes and asset allowlist; no arbitrary filesystem paths."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
router = APIRouter(tags=['Enterprise workspace UI'])
ROOT = Path(__file__).resolve().parent / 'web_workspace'
ROUTES = json.loads((ROOT / 'routes.json').read_text('utf-8'))

def shell():
    return FileResponse(ROOT / 'index.html', media_type='text/html; charset=utf-8', headers={'Cache-Control':'no-store'})

@router.get('/', include_in_schema=False)
def home():
    return RedirectResponse('/institution/dashboard', status_code=307)

for route in ROUTES:
    # Public markup contains no identity or records; APIs are independent guards.
    router.add_api_route(route['path'].replace(':id', '{record_id}'), lambda record_id=None: shell(), methods=['GET'], include_in_schema=False)
for route in ('/login', '/mfa', '/forgot-password'):
    router.add_api_route(route, shell, methods=['GET'], include_in_schema=False)

ASSETS = {p.relative_to(ROOT).as_posix(): p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.js','.css','.json','.svg','.woff2','.txt'}}

@router.get('/workspace-assets/{asset:path}', include_in_schema=False)
def asset_file(asset: str):
    if asset not in ASSETS:
        raise HTTPException(404, 'asset not found')
    return FileResponse(ASSETS[asset], headers={'Cache-Control':'no-store'})
