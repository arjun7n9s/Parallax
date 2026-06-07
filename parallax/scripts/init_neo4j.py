#!/usr/bin/env python3
"""
Initialize Neo4j Constraints and Indexes for the TAIG Knowledge Graph.

Ensures that the 6 v2 node types have proper uniqueness constraints and
indexes applied for performance before any data is ingested.
"""
import asyncio
import logging
import sys

from neo4j import AsyncGraphDatabase

# Setup basic logging for the script
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("neo4j_init")

# Temporary hardcoded connection info for script initialization (in prod, load from env)
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "parallax_neo4j_pass"

# Cypher statements to create constraints
CONSTRAINTS = [
    # 1. Hypothesis: Must have unique ID
    "CREATE CONSTRAINT hypothesis_id IF NOT EXISTS FOR (h:Hypothesis) REQUIRE h.id IS UNIQUE",
    # 2. Experiment: Must have unique ID
    "CREATE CONSTRAINT experiment_id IF NOT EXISTS FOR (e:Experiment) REQUIRE e.id IS UNIQUE",
    # 3. Observation: Must have unique ID
    "CREATE CONSTRAINT observation_id IF NOT EXISTS FOR (o:Observation) REQUIRE o.id IS UNIQUE",
    # 4. TemporalFingerprint: Unique by hash/identifier
    "CREATE CONSTRAINT fingerprint_hash IF NOT EXISTS FOR (t:TemporalFingerprint) REQUIRE t.hash IS UNIQUE",
    # 5. Pattern: Unique name
    "CREATE CONSTRAINT pattern_name IF NOT EXISTS FOR (p:Pattern) REQUIRE p.name IS UNIQUE",
    # 6. FraudChainStage: Unique ID
    "CREATE CONSTRAINT fraudstage_id IF NOT EXISTS FOR (f:FraudChainStage) REQUIRE f.id IS UNIQUE",
    
    # Original TAIG Nodes Uniqueness
    "CREATE CONSTRAINT apk_sha256 IF NOT EXISTS FOR (a:APK) REQUIRE a.sha256 IS UNIQUE",
    "CREATE CONSTRAINT ip_address IF NOT EXISTS FOR (i:IPAddress) REQUIRE i.address IS UNIQUE",
    "CREATE CONSTRAINT domain_name IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE",
]

async def init_neo4j() -> None:
    logger.info("Connecting to Neo4j at %s...", NEO4J_URI)
    try:
        driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        async with driver.session() as session:
            for cypher in CONSTRAINTS:
                logger.info("Executing: %s", cypher)
                await session.run(cypher)
                
        logger.info("Successfully applied all Neo4j constraints.")
        await driver.close()
    except Exception as e:
        logger.error("Failed to initialize Neo4j: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_neo4j())
