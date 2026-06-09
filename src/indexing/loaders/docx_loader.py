from __future__ import annotations

from pathlib import Path

import docx
from docx.opc.exceptions import PackageNotFoundError
from docx.text.paragraph import Paragraph

from .base import (
    Document,
    DocumentBlock,
    DocumentLoader,
    DocumentParseError,
)


class DocxLoader(DocumentLoader):
    """
    Structured DOCX loader with semantic block extraction.

    Features
    --------
    - Preserves heading hierarchy
    - Extracts paragraph blocks
    - Extracts table content
    - Returns structured `Document.blocks`
    - Maintains backward-compatible `content`

    Supported semantic block types:
        - heading
        - paragraph
        - table

    Notes
    -----
    Heading levels are inferred from Word styles:

        Heading 1 -> level 1
        Heading 2 -> level 2
        ...

    This enables hierarchical / semantic chunking later
    in the indexing pipeline.
    """

    supported_extensions = (".docx", ".doc")

    def __init__(
        self,
        *,
        include_tables: bool = True,
        paragraph_separator: str = "\n",
    ) -> None:
        self.include_tables = include_tables
        self.paragraph_separator = paragraph_separator

    # ------------------------------------------------------------------ #
    # Core                                                                #
    # ------------------------------------------------------------------ #

    def _load(self, path: Path) -> Document:

        try:
            doc = docx.Document(str(path))

        except PackageNotFoundError as exc:
            raise DocumentParseError(
                path=str(path),
                reason=(
                    "python-docx could not open the file "
                    "(corrupt or invalid .docx)"
                ),
                original=exc,
            ) from exc

        blocks: list[DocumentBlock] = []

        # -------------------------------------------------------------- #
        # Paragraphs / headings                                           #
        # -------------------------------------------------------------- #

        for paragraph in doc.paragraphs:

            block = self._paragraph_to_block(paragraph)

            if block:
                blocks.append(block)

        # -------------------------------------------------------------- #
        # Tables                                                          #
        # -------------------------------------------------------------- #

        if self.include_tables:
            blocks.extend(self._extract_table_blocks(doc))

        if not blocks:
            raise DocumentParseError(
                path=str(path),
                reason="no extractable text found",
            )

        # Backward-compatible flattened content
        content = self.paragraph_separator.join(
            block.text for block in blocks
        )

        metadata = self._extract_metadata(doc, path)

        return Document(
            content=content,
            source=str(path),
            metadata=metadata,
            blocks=blocks,
        )

    # ------------------------------------------------------------------ #
    # Semantic extraction helpers                                         #
    # ------------------------------------------------------------------ #

    def _paragraph_to_block(
        self,
        paragraph: Paragraph,
    ) -> DocumentBlock | None:

        text = self._clean_text(paragraph.text)

        if not text:
            return None

        style_name = paragraph.style.name.strip()

        heading_level = self._detect_heading_level(style_name)

        # -------------------------------------------------------------- #
        # Heading                                                         #
        # -------------------------------------------------------------- #

        if heading_level is not None:

            return DocumentBlock(
                type="heading",
                text=text,
                level=heading_level,
            )

        # -------------------------------------------------------------- #
        # Normal paragraph                                                #
        # -------------------------------------------------------------- #

        return DocumentBlock(
            type="paragraph",
            text=text,
        )

    def _extract_table_blocks(
        self,
        doc: docx.Document,
    ) -> list[DocumentBlock]:

        """
        Flatten table cells into semantic table blocks.

        Each row becomes a single line:

            col1 | col2 | col3

        This preserves row semantics much better than
        flattening every cell independently.
        """

        blocks: list[DocumentBlock] = []

        for table in doc.tables:

            for row in table.rows:

                row_cells: list[str] = []

                for cell in row.cells:

                    text = self._clean_text(cell.text)

                    if text:
                        row_cells.append(text)

                if row_cells:

                    row_text = " | ".join(row_cells)

                    blocks.append(
                        DocumentBlock(
                            type="table",
                            text=row_text,
                        )
                    )

        return blocks

    # ------------------------------------------------------------------ #
    # Utility helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _detect_heading_level(
        style_name: str,
    ) -> int | None:
        """
        Detect heading level from Word style name.

        Examples
        --------
        Heading 1 -> 1
        Heading 2 -> 2
        """

        style_name = style_name.lower()

        if not style_name.startswith("heading"):
            return None

        parts = style_name.split()

        if len(parts) < 2:
            return None

        level_str = parts[1]

        if level_str.isdigit():
            return int(level_str)

        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Normalize whitespace and strip text.
        """

        return " ".join(text.split()).strip()

    @staticmethod
    def _extract_metadata(
        doc: docx.Document,
        path: Path,
    ) -> dict:

        props = doc.core_properties

        return {
            "title": props.title or "",
            "author": props.author or "",
            "subject": props.subject or "",
            "keywords": props.keywords or "",
            "created": (
                props.created.isoformat()
                if props.created
                else ""
            ),
            "modified": (
                props.modified.isoformat()
                if props.modified
                else ""
            ),
            "file_name": path.name,
        }

