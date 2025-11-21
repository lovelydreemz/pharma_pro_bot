
import os
from math import ceil
from typing import List
from pypdf import PdfReader
from database import insert_document, add_document_chunk

def read_pdf_text(file_path: str) -> List[str]:
    reader = PdfReader(file_path)
    pages_text = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages_text.append(text)
    return pages_text

def chunk_text(text: str, max_chars: int = 1200) -> List[str]:
    # Simple character-based chunking
    chunks = []
    text = text.replace("\r", "").replace("\n\n", "\n")
    current = []
    current_len = 0
    for line in text.split("\n"):
        if current_len + len(line) + 1 > max_chars:
            if current:
                chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks

def ingest_pdf(title: str, src_path: str, dest_folder: str, uploaded_by_user_id: int):
    os.makedirs(dest_folder, exist_ok=True)
    filename = os.path.basename(src_path)
    dest_path = os.path.join(dest_folder, filename)
    if src_path != dest_path:
        os.replace(src_path, dest_path)

    pages_text = read_pdf_text(dest_path)
    doc_id = insert_document(
        title=title,
        filename=filename,
        pages=len(pages_text),
        uploaded_by_user_id=uploaded_by_user_id,
        status="approved",
    )

    combined_text = "\n".join(pages_text)
    chunks = chunk_text(combined_text)
    for idx, chunk in enumerate(chunks):
        token_count = len(chunk.split())
        add_document_chunk(doc_id, idx, chunk, token_count)

    return doc_id, len(chunks)
