"""Provider factory: returns mock IQ provider instances for tool-based agents.

This is the single import point for all grounding providers used by MAF tools
(foundry_iq_tools, fabric_iq_tools, work_iq_tools).  Agents and tools MUST
import from here — never from grounding.mock.* directly.

Note: USE_REAL_IQ only affects the curator agent's context_provider wiring
(see agents/curator.py). Tool-based agents (study plan, engagement) always use
mock providers regardless of USE_REAL_IQ, since their real adapters are not
yet implemented.

Usage::

    from grounding.factory import IQProviderFactory

    factory = IQProviderFactory()
    foundry = factory.foundry()
    fabric  = factory.fabric()
    work    = factory.work()
"""
from __future__ import annotations

from grounding.base import FabricIQProvider, FoundryIQProvider, WorkIQProvider


class IQProviderFactory:
    """Factory that wires mock IQ providers for tool-based agents.

    Always returns mock providers — deterministic, no Azure credentials required.
    The curator agent's real grounding path goes through context_providers, not here.
    """

    def foundry(self) -> FoundryIQProvider:
        """Return the mock Foundry IQ provider (ChromaDB)."""
        from grounding.mock.foundry import MockFoundryIQProvider  # noqa: PLC0415

        return MockFoundryIQProvider()

    def fabric(self) -> FabricIQProvider:
        """Return the mock Fabric IQ provider (fixture files)."""
        from grounding.mock.fabric import MockFabricIQProvider  # noqa: PLC0415

        return MockFabricIQProvider()

    def work(self) -> WorkIQProvider:
        """Return the mock Work IQ provider (calendar fixtures)."""
        from grounding.mock.work import MockWorkIQProvider  # noqa: PLC0415

        return MockWorkIQProvider()
