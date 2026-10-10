"""G8 same-origin local studio UI; authenticated APIs independently enforce RBAC."""
from pathlib import Path
from typing import Literal
from fastapi import APIRouter
from fastapi.responses import FileResponse

router=APIRouter(tags=["G8 UI"])
WEB_DIR=Path(__file__).resolve().parent / "web_g8"

@router.get("/ui/intelligence", include_in_schema=False)
def studio():
    return FileResponse(WEB_DIR / "index.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control":"no-store"})

@router.get("/ui/intelligence/assets/{asset}", include_in_schema=False)
def studio_asset(asset: Literal["studio.css", "studio.js"]):
    media = ("text/css; charset=utf-8" if asset == "studio.css"
             else "text/javascript; charset=utf-8")
    return FileResponse(WEB_DIR / asset, media_type=media,
        headers={"Cache-Control":"no-store"})
