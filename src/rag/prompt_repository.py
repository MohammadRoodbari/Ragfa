from __future__ import annotations

from functools import lru_cache
from pathlib import Path


class PromptRepository:
    """
    Loads prompt templates from disk.

    Prompt files are cached after the first read to avoid repeated
    filesystem access during application lifetime.
    """

    _PROMPTS_DIR = Path(__file__).parent / "prompts"

    @classmethod
    @lru_cache(maxsize=None)
    def load(cls, filename: str) -> str:
        """
        Load a prompt file.

        Args:
            filename: Prompt filename inside the prompts directory.

        Returns:
            Prompt text.
        """
        path = cls._PROMPTS_DIR / filename

        return path.read_text(encoding="utf-8").strip()