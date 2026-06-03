"""
ForensIQ – File Parsing Utilities
==================================
Extracts plain text from uploaded files so the agent can process them.

Supported formats:
    • .txt   – read as UTF-8 text
    • .pdf   – extracted via PyPDF2
    • .docx  – extracted via python-docx
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Union

import streamlit as st


def extract_text_from_file(uploaded_file) -> str:
    """
    Accept a Streamlit ``UploadedFile`` object (or a file-like object with
    a ``.name`` attribute) and return the full text content as a string.

    Parameters
    ----------
    uploaded_file : streamlit.runtime.uploaded_file_manager.UploadedFile
        The file uploaded through ``st.file_uploader``.

    Returns
    -------
    str
        Extracted plain-text content.

    Raises
    ------
    ValueError
        If the file extension is not supported.
    RuntimeError
        If a parsing library is missing.
    """
    filename: str = uploaded_file.name.lower()
    raw_bytes: bytes = uploaded_file.read()

    # ── TXT ──────────────────────────────────────────────────────────────
    if filename.endswith(".txt"):
        return raw_bytes.decode("utf-8", errors="replace")

    # ── PDF ──────────────────────────────────────────────────────────────
    if filename.endswith(".pdf"):
        try:
            from PyPDF2 import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "PyPDF2 is required for PDF parsing. "
                "Install it with: pip install PyPDF2"
            ) from exc

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages).strip()

    # ── DOCX ─────────────────────────────────────────────────────────────
    if filename.endswith(".docx"):
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError(
                "python-docx is required for DOCX parsing. "
                "Install it with: pip install python-docx"
            ) from exc

        doc = Document(io.BytesIO(raw_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs).strip()

    # ── Unsupported ──────────────────────────────────────────────────────
    supported = {".txt", ".pdf", ".docx"}
    raise ValueError(
        f"Unsupported file type: '{Path(filename).suffix}'. "
        f"Supported formats: {supported}"
    )
