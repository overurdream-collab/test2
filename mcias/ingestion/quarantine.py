"""Machine-readable isolation reasons."""
def item(reason: str, kind: str = "file", index: int = 1) -> dict:
    return {"reason": reason, "locator": {"kind": kind, "index": index}}
