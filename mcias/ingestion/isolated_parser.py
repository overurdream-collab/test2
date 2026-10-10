"""Deterministic text extraction in a bounded child process."""
import multiprocessing as mp
import queue

class ParserTimeout(RuntimeError):
    pass

def _run(kind, data, output):
    try:
        if kind == "pdf":
            from mcias.ingestion.parsers.pdf_parser import parse
        elif kind == "xlsx":
            from mcias.ingestion.parsers.excel_parser import parse
        elif kind == "csv":
            from mcias.ingestion.parsers.csv_parser import parse
        elif kind == "image":
            from mcias.ingestion.parsers.image_parser import parse
        else:
            raise ValueError("unsupported format")
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CPU, (25, 26))
        except (ImportError, OSError, ValueError):
            pass
        result = parse(data)
        output.put(("ok", result))
    except Exception as exc:
        output.put(("error", type(exc).__name__))

def isolated_parse(kind: str, data: bytes, timeout: int = 30):
    context = mp.get_context("spawn")
    output = context.Queue(maxsize=1)
    worker = context.Process(target=_run, args=(kind, data, output), daemon=True)
    worker.start()
    try:
        try:
            status, result = output.get(timeout=timeout)
        except queue.Empty as exc:
            raise ParserTimeout("parser timed out") from exc
        if status != "ok":
            raise ValueError("parser rejected source: " + result)
        return result
    finally:
        if worker.is_alive():
            worker.terminate()
        worker.join(timeout=3)
        if worker.is_alive():
            worker.kill()
            worker.join(timeout=3)
        output.close()
