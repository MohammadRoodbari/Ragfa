from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal


# ------------------------------------------------------------------ #
# Structured blocks                                                   #
# ------------------------------------------------------------------ #

BlockType = Literal[
    "heading",
    "paragraph",
    "table",
    "list",
]


@dataclass
class DocumentBlock:
    """
    Structured semantic block extracted from a document.
    """

    type: BlockType
    text: str
    level: int | None = None

    def __post_init__(self) -> None:
        self.text = self.text.strip()


# ------------------------------------------------------------------ #
# Main document model                                                 #
# ------------------------------------------------------------------ #

@dataclass
class Document:
    """
    Represents a parsed document.

    `content` remains for backward compatibility.
    `blocks` enables semantic/hierarchical chunking.
    """

    content: str
    source: str
    metadata: dict = field(default_factory=dict)

    # NEW
    blocks: list[DocumentBlock] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError(
                f"Document loaded from '{self.source}' has empty content."
            )


# ------------------------------------------------------------------ #
# Base loader                                                         #
# ------------------------------------------------------------------ #

class DocumentLoader(ABC):

    supported_extensions: tuple[str, ...]

    def load(self, path: str | Path) -> Document:
        path = Path(path).resolve()
        self._validate_path(path)
        return self._load(path)

    def load_dir(
        self,
        dir_path: str | Path,
        *,
        recursive: bool = True,
    ) -> Iterator[Document]:

        dir_path = Path(dir_path).resolve()

        if not dir_path.is_dir():
            raise NotADirectoryError(f"'{dir_path}' is not a directory.")

        pattern = "**/*" if recursive else "*"

        for file_path in sorted(dir_path.glob(pattern)):
            if (
                file_path.is_file()
                and file_path.suffix.lower() in self.supported_extensions
            ):
                try:
                    yield self.load(file_path)

                except Exception as exc:
                    self._on_load_error(file_path, exc)

    def _validate_path(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"File not found: '{path}'")

        ext = path.suffix.lower()

        if ext not in self.supported_extensions:
            raise UnsupportedFileTypeError(
                loader=type(self).__name__,
                path=str(path),
                extension=ext,
                supported=self.supported_extensions,
            )

    def _on_load_error(self, path: Path, exc: Exception) -> None:
        print(f"[WARNING] Skipping '{path}': {exc}")

    @abstractmethod
    def _load(self, path: Path) -> Document:
        ...


# ------------------------------------------------------------------ #
# Exceptions                                                          #
# ------------------------------------------------------------------ #

class UnsupportedFileTypeError(ValueError):

    def __init__(
        self,
        *,
        loader: str,
        path: str,
        extension: str,
        supported: tuple[str, ...],
    ) -> None:

        super().__init__(
            f"{loader} does not support '{extension}' "
            f"(file: '{path}'). Supported: {supported}"
        )


class DocumentParseError(RuntimeError):

    def __init__(
        self,
        path: str,
        reason: str,
        original: Exception | None = None,
    ) -> None:

        super().__init__(f"Failed to parse '{path}': {reason}")

        self.path = path
        self.reason = reason
        self.__cause__ = original
