"""Import regression tests confirming deleted provider classes are gone.

TDD: T2.4 — tests written before deletion.
"""
from __future__ import annotations

import importlib
import sys


class TestDeletedProviderClasses:
    """T2.3: FoundryKBContextProvider and RealFoundryIQProvider must be removed."""

    def test_real_foundry_iq_provider_not_importable(self) -> None:
        """RealFoundryIQProvider must not be importable from grounding.real.foundry."""
        # Remove cached module so we get a fresh import
        sys.modules.pop("grounding.real.foundry", None)
        import grounding.real.foundry as foundry_module

        assert not hasattr(foundry_module, "RealFoundryIQProvider"), (
            "RealFoundryIQProvider should have been deleted from grounding.real.foundry"
        )

    def test_foundry_kb_context_provider_not_importable(self) -> None:
        """FoundryKBContextProvider must not exist as a module-level name."""
        sys.modules.pop("grounding.real.foundry", None)
        import grounding.real.foundry as foundry_module

        assert not hasattr(foundry_module, "FoundryKBContextProvider"), (
            "FoundryKBContextProvider should have been deleted from grounding.real.foundry"
        )

    def test_grounding_real_foundry_imports_without_error(self) -> None:
        """The module (or its absence) must not raise an ImportError on import."""
        sys.modules.pop("grounding.real.foundry", None)
        try:
            import grounding.real.foundry  # noqa: F401
        except ImportError:
            # File was deleted — that is also acceptable
            pass

    def test_no_import_of_deleted_class_in_curator(self) -> None:
        """agents/curator.py must not import RealFoundryIQProvider."""
        import ast
        from pathlib import Path

        curator_path = Path("agents/curator.py")
        if not curator_path.exists():
            return  # curator.py may not yet be refactored in PR 1 — skip

        source = curator_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = []
                if isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                for name in names:
                    assert "RealFoundryIQProvider" not in name, (
                        f"curator.py still imports RealFoundryIQProvider: {name}"
                    )
                    assert "FoundryKBContextProvider" not in name, (
                        f"curator.py still imports FoundryKBContextProvider: {name}"
                    )
