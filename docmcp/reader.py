import logging
import os
import re

import fitz

logger = logging.getLogger("docmcp.reader")

MAX_PAGES = int(os.environ.get("DOCMCP_MAX_PAGES", "100"))


def _safe_open(path: str) -> fitz.Document:
    try:
        doc = fitz.open(path)
    except fitz.FileDataError as e:
        if "encrypted" in str(e).lower() or "password" in str(e).lower():
            raise ValueError(f"Cannot open encrypted PDF: {path}. Password-protected PDFs are not supported.")
        raise ValueError(f"Cannot open PDF: {e}")
    return doc


class PDFReader:
    def read(self, path: str, max_pages: int = MAX_PAGES) -> dict:
        if not os.path.isfile(path):
            return {"error": f"File not found: {path}"}
        try:
            doc = _safe_open(path)
        except ValueError as e:
            return {"error": str(e)}
        total_pages = len(doc)
        result = {
            "file": os.path.basename(path),
            "pages": min(total_pages, max_pages),
            "total_pages": total_pages,
            "text": "",
            "metadata": {},
            "tables": [],
            "images": [],
        }
        meta = doc.metadata
        if meta:
            result["metadata"] = {
                "title": (meta.get("title", "") or "")[:500],
                "author": (meta.get("author", "") or "")[:200],
                "subject": (meta.get("subject", "") or "")[:500],
                "keywords": (meta.get("keywords", "") or "")[:1000],
                "producer": (meta.get("producer", "") or "")[:200],
                "creator": (meta.get("creator", "") or "")[:200],
            }
        pages_to_read = min(total_pages, max_pages)
        if total_pages > max_pages:
            logger.warning(
                "PDF has %d pages, truncating to %d pages", total_pages, max_pages
            )
        page_texts = []
        for page_num in range(pages_to_read):
            page = doc[page_num]
            text = page.get_text()
            page_texts.append(f"\n\n--- Page {page_num + 1} ---\n\n{text}")
        result["text"] = "".join(page_texts).strip()
        doc.close()
        return result

    def info(self, path: str) -> dict:
        if not os.path.isfile(path):
            return {"error": f"File not found: {path}"}
        try:
            doc = _safe_open(path)
        except ValueError as e:
            return {"error": str(e)}
        meta = doc.metadata
        info = {
            "file": os.path.basename(path),
            "size_bytes": os.path.getsize(path),
            "size_kb": round(os.path.getsize(path) / 1024, 1),
            "pages": len(doc),
            "has_toc": bool(doc.get_toc()),
            "has_images": False,
            "image_count": 0,
        }
        if meta:
            info["title"] = (meta.get("title", "") or "")[:500]
            info["author"] = (meta.get("author", "") or "")[:200]
            info["subject"] = (meta.get("subject", "") or "")[:500]
            info["producer"] = (meta.get("producer", "") or "")[:200]
            info["creator"] = (meta.get("creator", "") or "")[:200]
        image_count = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_count += len(page.get_images())
        info["has_images"] = image_count > 0
        info["image_count"] = image_count
        doc.close()
        return info

    def extract_images(self, path: str, output_dir: str = "") -> dict:
        if not os.path.isfile(path):
            return {"error": f"File not found: {path}"}
        try:
            doc = _safe_open(path)
        except ValueError as e:
            return {"error": str(e)}
        if not output_dir:
            output_dir = os.path.dirname(path) or "."
        os.makedirs(output_dir, exist_ok=True)
        extracted = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            for img_idx, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                if len(image_bytes) > 50 * 1024 * 1024:
                    logger.warning("Skipping image %d on page %d: too large (%d bytes)", img_idx + 1, page_num + 1, len(image_bytes))
                    continue
                name = f"page{page_num + 1}_img{img_idx + 1}.{ext}"
                img_path = os.path.join(output_dir, name)
                with open(img_path, "wb") as f:
                    f.write(image_bytes)
                extracted.append({
                    "page": page_num + 1,
                    "index": img_idx + 1,
                    "size_bytes": len(image_bytes),
                    "ext": ext,
                    "path": img_path,
                })
        doc.close()
        return {
            "total_images": len(extracted),
            "images": extracted,
        }

    def to_markdown(self, path: str) -> str:
        data = self.read(path)
        if "error" in data:
            return data["error"]
        md = []
        if data["metadata"].get("title"):
            md.append(f"# {data['metadata']['title']}\n")
        if data["metadata"].get("author"):
            md.append(f"**Author:** {data['metadata']['author']}  \n")
        md.append(f"**Pages:** {data['pages']}  \n")
        md.append(f"**File:** {data['file']}  \n")
        md.append("---\n")
        text = data["text"]
        text = re.sub(r'\n{3,}', '\n\n', text)
        md.append(text)
        return "\n".join(md)
