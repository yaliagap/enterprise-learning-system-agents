"""Tests for search_knowledge_base async @tool function.

TDD: T2.2 — tests written before implementation.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: build a fake SSE response body
# ---------------------------------------------------------------------------


def _sse_body(text: str) -> bytes:
    """Produce minimal SSE response bytes with one data: line."""
    payload = {"result": {"content": [{"text": text}]}}
    return f"data: {json.dumps(payload)}\n\n".encode()


def _sse_no_data() -> bytes:
    """SSE response with no data: line."""
    return b"event: ping\n\n"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSearchKnowledgeBase:
    """Capability 2: KB HTTP wrapper tool."""

    @pytest.mark.asyncio
    async def test_mock_branch_returns_fixture_string_without_http(self) -> None:
        """When USE_REAL_IQ is false, tool returns deterministic mock without any HTTP."""
        with patch("config.USE_REAL_IQ", False):
            from agents.tools.foundry_iq_tools import search_knowledge_base

            result = await search_knowledge_base("Azure certifications for AI Engineer")
            assert isinstance(result, str)
            assert len(result) > 0
            # Should be a fixture string, not an error
            assert "Knowledge base search failed" not in result

    @pytest.mark.asyncio
    async def test_query_over_400_chars_is_truncated(self) -> None:
        """Query longer than 400 chars is truncated before the POST call."""
        long_query = "x" * 500
        captured: dict = {}

        async def fake_post(url: str, **kwargs):
            captured["sent_query"] = kwargs.get("json", {}).get("queries", [None])[0]
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = _sse_body("Some KB answer about Azure certs.")
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("config.USE_REAL_IQ", True), \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_client

            from agents.tools import foundry_iq_tools
            import importlib
            importlib.reload(foundry_iq_tools)

            result = await foundry_iq_tools.search_knowledge_base(long_query)
            # The actual query sent must be <= 400 chars
            if "sent_query" in captured:
                assert len(captured["sent_query"]) <= 400

    @pytest.mark.asyncio
    async def test_successful_sse_parse_returns_text(self) -> None:
        """Successful SSE response is parsed and plain text is returned."""
        expected_text = "AI-900 is recommended for beginners. [ref_id:1]"

        async def fake_post(url: str, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = _sse_body(expected_text)
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("config.USE_REAL_IQ", True), \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_client

            from agents.tools import foundry_iq_tools
            import importlib
            importlib.reload(foundry_iq_tools)

            result = await foundry_iq_tools.search_knowledge_base("AI certs")
            assert result == expected_text

    @pytest.mark.asyncio
    async def test_http_error_returns_error_string_no_exception(self) -> None:
        """HTTP 4xx returns an error string; no unhandled exception is raised."""
        import httpx

        async def fake_post(url: str, **kwargs):
            raise httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )

        with patch("config.USE_REAL_IQ", True), \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_client

            from agents.tools import foundry_iq_tools
            import importlib
            importlib.reload(foundry_iq_tools)

            result = await foundry_iq_tools.search_knowledge_base("some query")
            assert isinstance(result, str)
            assert "Knowledge base search failed" in result

    @pytest.mark.asyncio
    async def test_no_data_line_in_sse_returns_error_string(self) -> None:
        """SSE response with no data: line returns an error string."""

        async def fake_post(url: str, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = _sse_no_data()
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("config.USE_REAL_IQ", True), \
             patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_client

            from agents.tools import foundry_iq_tools
            import importlib
            importlib.reload(foundry_iq_tools)

            result = await foundry_iq_tools.search_knowledge_base("query without data line")
            assert isinstance(result, str)
            assert "Knowledge base search failed" in result
