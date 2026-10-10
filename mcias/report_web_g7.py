"""G7 local-only static reporting UI; HTML and assets are public, data is not."""
from pathlib import Path
from typing import Literal
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["G7 UI"])
ASSETS = Path(__file__).resolve().parent / "web_g7"

@router.get("/ui/reports", include_in_schema=False)
def reporting_ui():
    return FileResponse(ASSETS / "index.html", media_type="text/html; charset=utf-8",
                        headers={"Cache-Control":"no-store"})

@router.get("/ui/reports/assets/{asset}", include_in_schema=False)
def reporting_asset(asset: Literal["dashboard.css","dashboard.js"]):
    media = "text/css; charset=utf-8" if asset.endswith(".css") else "text/javascript; charset=utf-8"
    return FileResponse(ASSETS / asset, media_type=media,
                        headers={"Cache-Control":"no-store"})
