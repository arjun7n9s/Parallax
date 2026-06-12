"""Async Neo4j client for the TAIG knowledge graph.

A thin wrapper over the official async driver with a lazily-created singleton,
read/write helpers, and a read-only query guard used by the threat-hunting API
(no mutating clauses may reach the graph from user-supplied Cypher).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from parallax.core.config import settings

logger = logging.getLogger(__name__)

# Mutating / admin Cypher clauses forbidden in user-supplied hunt queries.
_FORBIDDEN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|CALL\s+db\.|LOAD\s+CSV|"
    r"FOREACH|CREATE\s+INDEX|CREATE\s+CONSTRAINT)\b",
    re.IGNORECASE,
)


class Neo4jClient:
    def __init__(self) -> None:
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        return self._driver

    async def run_write(self, cypher: str, **params: Any) -> list[dict]:
        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(cypher, **params)
            return [record.data() async for record in result]

    async def run_read(self, cypher: str, **params: Any) -> list[dict]:
        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(cypher, **params)
            return [record.data() async for record in result]

    async def run_safe_read(self, cypher: str, **params: Any) -> list[dict]:
        """Run a read-only query, rejecting any mutating/admin clauses."""
        if _FORBIDDEN.search(cypher):
            raise ValueError("Only read-only Cypher is permitted via this endpoint.")
        return await self.run_read(cypher, **params)

    async def ping(self) -> bool:
        try:
            rows = await self.run_read("RETURN 1 AS ok")
            return bool(rows and rows[0].get("ok") == 1)
        except Exception as exc:
            logger.warning("Neo4j ping failed: %s", exc)
            return False

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None


neo4j_client = Neo4jClient()
