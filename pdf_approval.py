
import os
from typing import Tuple
from config import PENDING_PDFS_FOLDER, BOOKS_FOLDER
from database import insert_document, update_document_status, add_document_chunk, get_document
from pdf_ingest import read_pdf_text, chunk_text

def save_pending_pdf(file_path: str, original_filename: str) -> str:
    os.makedirs(PENDING_PDFS_FOLDER, exist_ok=True)
    dest_path = os.path.join(PENDING_PDFS_FOLDER, original_filename)
    if os.path.exists(dest_path):
        # avoid overwrite
        base, ext = os.path.splitext(original_filename)
        dest_path = os.path.join(PENDING_PDFS_FOLDER, f"{base}_1{ext}")
    os.replace(file_path, dest_path)
    return dest_path

def approve_pending_pdf(doc_id: int, admin_user_id: int) -> Tuple[bool, str]:
    doc = get_document(doc_id)
    if not doc:
        return False, "Document not found."

    pending_path = os.path.join(PENDING_PDFS_FOLDER, doc["filename"])
    if not os.path.exists(pending_path):
        return False, "Pending PDF file not found on server."

    os.makedirs(BOOKS_FOLDER, exist_ok=True)
    approved_path = os.path.join(BOOKS_FOLDER, doc["filename"])
    os.replace(pending_path, approved_path)

    pages_text = read_pdf_text(approved_path)
    combined = "\n".join(pages_text)
    chunks = chunk_text(combined)

    for idx, chunk in enumerate(chunks):
        token_count = len(chunk.split())
        add_document_chunk(doc["id"], idx, chunk, token_count)

    update_document_status(doc["id"], "approved", admin_user_id)
    return True, f"Document {doc_id} approved with {len(chunks)} chunks."
