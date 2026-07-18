import pytest
import os
from unittest.mock import patch, MagicMock
from servers.doc import read, info, extract_images, to_markdown, merge, split, extract_pages, compress, generate_report, generate_table, generate_text

@pytest.fixture
def mock_reader():
    with patch("servers.doc.reader") as mock:
        yield mock

@pytest.fixture
def mock_manip():
    with patch("servers.doc.manip") as mock:
        yield mock

@pytest.fixture
def mock_gen():
    with patch("servers.doc.gen") as mock:
        yield mock

@pytest.fixture
def mock_validate():
    with patch("servers.doc._validate_doc_path", side_effect=lambda x: f"/mock/path/{os.path.basename(x)}") as mock:
        yield mock

@pytest.fixture
def mock_safe_resolve():
    with patch("servers.doc._safe_resolve_output", side_effect=lambda x: f"/mock/out/{os.path.basename(x)}") as mock:
        yield mock

def test_read_tool(mock_reader, mock_validate):
    mock_reader.read.return_value = {"file": "test.pdf", "pages": 5, "metadata": {}, "text": "Hello PDF"}
    result = read("test.pdf")
    assert "Hello PDF" in result
    mock_reader.read.assert_called_once_with("/mock/path/test.pdf")

def test_info_tool(mock_reader, mock_validate):
    mock_reader.info.return_value = {"pages": 10}
    result = info("test.pdf")
    assert "pages" in result
    mock_reader.info.assert_called_once_with("/mock/path/test.pdf")

def test_extract_images_tool(mock_reader, mock_validate):
    with patch("servers.doc._resolve", return_value="/mock/out/imgs"):
        mock_reader.extract_images.return_value = {"images_extracted": 3}
        result = extract_images("test.pdf", "imgs")
        assert "images_extracted" in result
        mock_reader.extract_images.assert_called_once_with("/mock/path/test.pdf", "/mock/out/imgs")

def test_merge_tool(mock_manip, mock_validate, mock_safe_resolve):
    mock_manip.merge.return_value = {"status": "merged"}
    result = merge("file1.pdf, file2.pdf", "out.pdf")
    assert "merged" in result
    mock_manip.merge.assert_called_once_with(["/mock/path/file1.pdf", "/mock/path/file2.pdf"], "/mock/out/out.pdf")

def test_generate_table_tool(mock_gen, mock_safe_resolve):
    result = generate_table("Title", "Col1,Col2", '[["A","B"]]', "out.pdf")
    assert "Generated" in result
    mock_gen.table_report.assert_called_once_with("Title", ["Col1", "Col2"], [["A", "B"]], "/mock/out/out.pdf")

def test_generate_table_invalid_json():
    result = generate_table("Title", "Col1,Col2", "invalid", "out.pdf")
    assert "Invalid JSON" in result

def test_generate_text_tool(mock_gen, mock_safe_resolve):
    mock_gen.text_to_pdf.return_value = {"status": "done"}
    result = generate_text("Some text", "out.pdf", "Title")
    assert "done" in result
    mock_gen.text_to_pdf.assert_called_once_with("Some text", "/mock/out/out.pdf", "Title")
