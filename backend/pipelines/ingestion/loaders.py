import logging
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".html", ".htm", ".txt", ".md"}


def is_supported(filepath: str) -> bool:
    return Path(filepath).suffix.lower() in SUPPORTED_EXTENSIONS


def load_pdf(filepath: str) -> list[Document]:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                pages.append(
                    Document(
                        page_content=text,
                        metadata={"source": filepath, "page": i + 1},
                    )
                )
        doc.close()
        logger.info(f"PDF loaded: {filepath} ({len(pages)} pages)")
        return pages
    except Exception as e:
        logger.error(f"Failed to load PDF {filepath}: {e}")
        raise


def load_docx(filepath: str) -> list[Document]:
    try:
        import docx2txt
        text = docx2txt.process(filepath)
        if not text.strip():
            return []
        return [Document(page_content=text.strip(), metadata={"source": filepath})]
    except Exception as e:
        logger.error(f"Failed to load DOCX {filepath}: {e}")
        raise


def load_txt(filepath: str) -> list[Document]:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            text = f.read().strip()
        if not text:
            return []
        return [Document(page_content=text, metadata={"source": filepath})]
    except Exception as e:
        logger.error(f"Failed to load TXT {filepath}: {e}")
        raise


def load_html_file(filepath: str) -> list[Document]:
    try:
        import html2text
        from bs4 import BeautifulSoup

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        converter = html2text.HTML2Text()
        converter.ignore_links = True
        converter.ignore_images = True
        text = converter.handle(str(soup)).strip()

        if not text:
            return []
        return [Document(page_content=text, metadata={"source": filepath})]
    except Exception as e:
        logger.error(f"Failed to load HTML {filepath}: {e}")
        raise


def load_url(url: str) -> list[Document]:
    try:
        import requests
        import html2text
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=30, headers={"User-Agent": "RAG-Bot/1.0"})
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        converter = html2text.HTML2Text()
        converter.ignore_links = True
        converter.ignore_images = True
        text = converter.handle(str(soup)).strip()

        if not text:
            return []
        return [Document(page_content=text, metadata={"source": url})]
    except Exception as e:
        logger.error(f"Failed to load URL {url}: {e}")
        raise


def load_document(filepath: str) -> list[Document]:
    ext = Path(filepath).suffix.lower()
    loaders = {
        ".pdf": load_pdf,
        ".docx": load_docx,
        ".doc": load_docx,
        ".html": load_html_file,
        ".htm": load_html_file,
        ".txt": load_txt,
        ".md": load_txt,
    }
    loader_fn = loaders.get(ext)
    if not loader_fn:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader_fn(filepath)
