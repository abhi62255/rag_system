import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class BaseDocumentLoader(ABC):
    """Abstract base class for document loaders."""

    @abstractmethod
    def load(self, filepath: str) -> List[Document]:
        """Load document from the given filepath and return a list of Documents."""
        pass


class PDFDocumentLoader(BaseDocumentLoader):
    """Loader for PDF documents using PyMuPDF (fitz)."""

    def load(self, filepath: str) -> List[Document]:
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


class DocxDocumentLoader(BaseDocumentLoader):
    """Loader for Word documents using docx2txt."""

    def load(self, filepath: str) -> List[Document]:
        try:
            import docx2txt
            text = docx2txt.process(filepath)
            if not text.strip():
                return []
            return [Document(page_content=text.strip(), metadata={"source": filepath})]
        except Exception as e:
            logger.error(f"Failed to load DOCX {filepath}: {e}")
            raise


class TextDocumentLoader(BaseDocumentLoader):
    """Loader for plain text documents."""

    def load(self, filepath: str) -> List[Document]:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
            if not text:
                return []
            return [Document(page_content=text, metadata={"source": filepath})]
        except Exception as e:
            logger.error(f"Failed to load TXT {filepath}: {e}")
            raise


class HTMLDocumentLoader(BaseDocumentLoader):
    """Loader for HTML documents parsing and converting markup to markdown."""

    def load(self, filepath: str) -> List[Document]:
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


class URLLoader:
    """Loader for web page content from a URL."""

    def load(self, url: str) -> List[Document]:
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


class LoaderRegistry:
    """Registry to map file extensions to loaders and load documents."""

    def __init__(self):
        self._loaders: Dict[str, BaseDocumentLoader] = {}
        # Register default loaders
        self.register_loader(".pdf", PDFDocumentLoader())
        self.register_loader(".docx", DocxDocumentLoader())
        self.register_loader(".doc", DocxDocumentLoader())
        self.register_loader(".html", HTMLDocumentLoader())
        self.register_loader(".htm", HTMLDocumentLoader())
        self.register_loader(".txt", TextDocumentLoader())
        self.register_loader(".md", TextDocumentLoader())

    def register_loader(self, ext: str, loader: BaseDocumentLoader):
        """Register a loader for a specific extension."""
        self._loaders[ext.lower()] = loader

    def is_supported(self, filepath: str) -> bool:
        """Check if file extension is supported."""
        ext = Path(filepath).suffix.lower()
        return ext in self._loaders

    def load_document(self, filepath: str) -> List[Document]:
        """Dispatch document loading to registered loaders."""
        ext = Path(filepath).suffix.lower()
        loader = self._loaders.get(ext)
        if not loader:
            raise ValueError(f"Unsupported file type: {ext}")
        return loader.load(filepath)
