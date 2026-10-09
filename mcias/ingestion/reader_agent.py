"""G2 ReaderAgent: deterministic extraction, explicit uncertainty."""
from mcias.ingestion.file_scanner import identify
from mcias.ingestion.parsers import csv_parser, excel_parser, pdf_parser, image_parser

PARSERS = {"csv": csv_parser.parse, "xlsx": excel_parser.parse, "pdf": pdf_parser.parse, "image": image_parser.parse}

def read(data: bytes, filename: str):
    kind = identify(data, filename)
    return PARSERS[kind](data)
