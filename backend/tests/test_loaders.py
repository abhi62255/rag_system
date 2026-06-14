import os
import tempfile
from pipelines.ingestion.loaders import LoaderRegistry, TextDocumentLoader


def test_loader_registry_supported_extensions():
    registry = LoaderRegistry()
    assert registry.is_supported("test.pdf") is True
    assert registry.is_supported("test.docx") is True
    assert registry.is_supported("test.doc") is True
    assert registry.is_supported("test.txt") is True
    assert registry.is_supported("test.md") is True
    assert registry.is_supported("test.html") is True
    assert registry.is_supported("test.png") is False


def test_text_loader_loads_content():
    loader = TextDocumentLoader()
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w+", delete=False, encoding="utf-8") as f:
        f.write("Hello World, testing text loader.")
        temp_name = f.name

    try:
        docs = loader.load(temp_name)
        assert len(docs) == 1
        assert docs[0].page_content == "Hello World, testing text loader."
        assert docs[0].metadata["source"] == temp_name
    finally:
        os.remove(temp_name)


def test_loader_registry_dispatches_correctly():
    registry = LoaderRegistry()
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w+", delete=False, encoding="utf-8") as f:
        f.write("Registry dispatch test.")
        temp_name = f.name

    try:
        docs = registry.load_document(temp_name)
        assert len(docs) == 1
        assert docs[0].page_content == "Registry dispatch test."
    finally:
        os.remove(temp_name)
