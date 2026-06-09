from __future__ import annotations

from pathlib import Path

import fitz

from .base import Document, DocumentLoader, DocumentParseError


class PdfLoader(DocumentLoader):
    """
    Loads text from PDF files using PyMuPDF (fitz).

    Parameters
    ----------
    page_separator:
        String inserted between consecutive pages in the final text.
        Defaults to a newline so that page breaks are preserved but
        don't introduce blank lines into the corpus.
    """

    supported_extensions = (".pdf",)

    def __init__(
        self,
        *,
        page_separator: str = "\n",
    ) -> None:
        self.page_separator = page_separator

    def _load(self, path: Path) -> Document:
        try:
            doc = fitz.open(path)
        except Exception as exc:
            raise DocumentParseError(
                path=str(path),
                reason="PyMuPDF could not open the file",
                original=exc,
            ) from exc

        try:
            pages: list[str] = []

            for page_num in range(min(len(doc), 1000000)):
                page = doc[page_num]
                text = page.get_text("text").strip()

                if text:
                    pages.append(text)
                else:
                    print(
                        f"[WARNING] '{path}' page {page_num + 1} yielded no text "
                        "(possibly a scanned image page)."
                    )

            if not pages:
                raise DocumentParseError(
                    path=str(path),
                    reason="no extractable text found in any page",
                )

            content = self.page_separator.join(pages)
            metadata = self._extract_metadata(doc, path)

            return Document(content=content, source=str(path), metadata=metadata)

        finally:
            doc.close()

    @staticmethod
    def _extract_metadata(doc: fitz.Document, path: Path) -> dict:
        meta = doc.metadata or {}
        return {
            "num_pages": doc.page_count,
            "title": meta.get("title", "") or "",
            "author": meta.get("author", "") or "",
            "subject": meta.get("subject", "") or "",
            "creator": meta.get("creator", "") or "",
            "file_name": path.name,
        }