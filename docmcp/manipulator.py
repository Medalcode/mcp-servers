import os

from pypdf import PdfReader, PdfWriter
import fitz


class PDFManipulator:
    def merge(self, paths: list[str], output: str) -> dict:
        writer = PdfWriter()
        sources = []
        for path in paths:
            if not os.path.isfile(path):
                return {"error": f"File not found: {path}"}
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
            sources.append(os.path.basename(path))
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "wb") as f:
            writer.write(f)
        return {
            "output": output,
            "sources": sources,
            "total_pages": len(writer.pages),
        }

    def split(self, path: str, output_dir: str = "") -> dict:
        if not os.path.isfile(path):
            return {"error": f"File not found: {path}"}
        reader = PdfReader(path)
        if not output_dir:
            output_dir = os.path.dirname(path) or "."
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(path))[0]
        pages = []
        for i, page in enumerate(reader.pages):
            writer = PdfWriter()
            writer.add_page(page)
            out = os.path.join(output_dir, f"{base}_page{i + 1}.pdf")
            with open(out, "wb") as f:
                writer.write(f)
            pages.append({"page": i + 1, "path": out})
        return {
            "source": os.path.basename(path),
            "total_pages": len(pages),
            "output_dir": output_dir,
            "pages": pages,
        }

    def extract_pages(self, path: str, pages: str, output: str) -> dict:
        if not os.path.isfile(path):
            return {"error": f"File not found: {path}"}
        reader = PdfReader(path)
        total = len(reader.pages)
        indices = set()
        for part in pages.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                indices.update(range(int(start) - 1, int(end)))
            else:
                indices.add(int(part) - 1)
        indices = sorted(i for i in indices if 0 <= i < total)
        if not indices:
            return {"error": f"No valid pages in range 1-{total}"}
        writer = PdfWriter()
        for i in indices:
            writer.add_page(reader.pages[i])
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "wb") as f:
            writer.write(f)
        return {
            "output": output,
            "source_pages": len(indices),
            "pages_extracted": [i + 1 for i in indices],
        }

    def compress(self, path: str, output: str) -> dict:
        if not os.path.isfile(path):
            return {"error": f"File not found: {path}"}
        original_size = os.path.getsize(path)
        doc = fitz.open(path)
        doc.save(output, garbage=4, deflate=True, clean=True)
        doc.close()
        new_size = os.path.getsize(output)
        return {
            "output": output,
            "original_bytes": original_size,
            "compressed_bytes": new_size,
            "saved_bytes": original_size - new_size,
            "saved_percent": round((1 - new_size / original_size) * 100, 1) if original_size > 0 else 0,
        }

    def set_metadata(self, path: str, title: str = "", author: str = "", subject: str = "") -> dict:
        if not os.path.isfile(path):
            return {"error": f"File not found: {path}"}
        reader = PdfReader(path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        meta = reader.metadata or {}
        if title:
            writer.add_metadata({"/Title": title})
        if author:
            writer.add_metadata({"/Author": author})
        if subject:
            writer.add_metadata({"/Subject": subject})
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            writer.write(f)
        os.replace(tmp, path)
        return {
            "file": path,
            "title": title or meta.get("/Title", ""),
            "author": author or meta.get("/Author", ""),
            "subject": subject or meta.get("/Subject", ""),
        }
