#!/usr/bin/env python3
"""
Initialize Neo4j Constraints and Indexes for the TAIG Knowledge Graph.

Creates uniqueness constraints and performance indexes for all node types
defined in 06_TAIG_SCHEMA.md. Property names match the schema exactly:
  - Hypothesis.hypothesis_id  (NOT .id)
  - Experiment.experiment_id   (NOT .id)
  - Observation.observation_id (NOT .id)
  - TemporalFingerprint.fingerprint_id (NOT .hash)
  - Pattern.pattern_id         (NOT .name)
  - FraudChainStage.stage_id   (NOT .id)

Run this script once after Neo4j is up:
  python scripts/init_neo4j.py
"""
import asyncio
import logging
import os
import sys

from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("neo4j_init")

# Read connection info from environment, with safe defaults for local dev
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "parallax_neo4j_pass")

# ──────────────────────────────────────────────────────────────
# Uniqueness constraints  (from 06_TAIG_SCHEMA.md §3.1–§3.17)
# ──────────────────────────────────────────────────────────────
CONSTRAINTS = [
    # §3.1  APK — primary key is sha256
    "CREATE CONSTRAINT apk_sha256_unique IF NOT EXISTS FOR (n:APK) REQUIRE n.sha256 IS UNIQUE",
    # §3.2  Permission
    "CREATE CONSTRAINT permission_name_unique IF NOT EXISTS FOR (n:Permission) REQUIRE n.name IS UNIQUE",
    # §3.3  API
    "CREATE CONSTRAINT api_fqn_unique IF NOT EXISTS FOR (n:API) REQUIRE n.fqn IS UNIQUE",
    # §3.4  IPAddress — schema key is .value
    "CREATE CONSTRAINT ip_value_unique IF NOT EXISTS FOR (n:IPAddress) REQUIRE n.value IS UNIQUE",
    # §3.5  Domain — schema key is .fqdn
    "CREATE CONSTRAINT domain_fqdn_unique IF NOT EXISTS FOR (n:Domain) REQUIRE n.fqdn IS UNIQUE",
    # §3.6  Certificate
    "CREATE CONSTRAINT cert_fingerprint_unique IF NOT EXISTS FOR (n:Certificate) REQUIRE n.fingerprint IS UNIQUE",
    # §3.7  ThreatActor
    "CREATE CONSTRAINT actor_name_unique IF NOT EXISTS FOR (n:ThreatActor) REQUIRE n.name IS UNIQUE",
    # §3.8  Campaign
    "CREATE CONSTRAINT campaign_name_unique IF NOT EXISTS FOR (n:Campaign) REQUIRE n.name IS UNIQUE",
    # §3.9  CodeBlob
    "CREATE CONSTRAINT blob_hash_unique IF NOT EXISTS FOR (n:CodeBlob) REQUIRE n.hash IS UNIQUE",
    # §3.10 BankApp
    "CREATE CONSTRAINT bankapp_package_unique IF NOT EXISTS FOR (n:BankApp) REQUIRE n.package IS UNIQUE",
    # §3.12 Hypothesis — key is hypothesis_id
    "CREATE CONSTRAINT hypothesis_id_unique IF NOT EXISTS FOR (n:Hypothesis) REQUIRE n.hypothesis_id IS UNIQUE",
    # §3.13 Experiment — key is experiment_id
    "CREATE CONSTRAINT experiment_id_unique IF NOT EXISTS FOR (n:Experiment) REQUIRE n.experiment_id IS UNIQUE",
    # §3.14 Observation — key is observation_id
    "CREATE CONSTRAINT observation_id_unique IF NOT EXISTS FOR (n:Observation) REQUIRE n.observation_id IS UNIQUE",
    # §3.15 TemporalFingerprint — key is fingerprint_id
    "CREATE CONSTRAINT temporal_fp_id_unique IF NOT EXISTS FOR (n:TemporalFingerprint) REQUIRE n.fingerprint_id IS UNIQUE",
    # §3.16 Pattern — key is pattern_id
    "CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS FOR (n:Pattern) REQUIRE n.pattern_id IS UNIQUE",
    # FraudChainStage has stage_id but schema only defines indexes (no uniqueness constraint)
    # Adding one anyway since stage_id is documented as the identity field
    "CREATE CONSTRAINT fraudstage_id_unique IF NOT EXISTS FOR (n:FraudChainStage) REQUIRE n.stage_id IS UNIQUE",
]

# ──────────────────────────────────────────────────────────────
# Performance indexes  (from 06_TAIG_SCHEMA.md)
# ──────────────────────────────────────────────────────────────
INDEXES = [
    # APK
    "CREATE INDEX apk_first_seen IF NOT EXISTS FOR (n:APK) ON (n.first_seen)",
    "CREATE INDEX apk_risk_score IF NOT EXISTS FOR (n:APK) ON (n.risk_score)",
    "CREATE INDEX apk_package IF NOT EXISTS FOR (n:APK) ON (n.package)",
    # Hypothesis
    "CREATE INDEX hypothesis_status IF NOT EXISTS FOR (n:Hypothesis) ON (n.status)",
    # Experiment
    "CREATE INDEX experiment_hypothesis IF NOT EXISTS FOR (n:Experiment) ON (n.hypothesis_id)",
    # Observation
    "CREATE INDEX observation_apk IF NOT EXISTS FOR (n:Observation) ON (n.apk_sha256)",
    "CREATE INDEX observation_type IF NOT EXISTS FOR (n:Observation) ON (n.observation_type)",
    # TemporalFingerprint
    "CREATE INDEX temporal_fp_family IF NOT EXISTS FOR (n:TemporalFingerprint) ON (n.malware_family)",
    # Pattern
    "CREATE INDEX pattern_category IF NOT EXISTS FOR (n:Pattern) ON (n.category)",
    "CREATE INDEX pattern_family IF NOT EXISTS FOR (n:Pattern) ON (n.malware_family)",
    # FraudChainStage
    "CREATE INDEX fraud_stage_apk IF NOT EXISTS FOR (n:FraudChainStage) ON (n.apk_sha256)",
    "CREATE INDEX fraud_stage_type IF NOT EXISTS FOR (n:FraudChainStage) ON (n.stage_type)",
]


async def init_neo4j() -> None:
    logger.info("Connecting to Neo4j at %s...", NEO4J_URI)
    try:
        driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        async with driver.session() as session:
            logger.info("--- Applying %d uniqueness constraints ---", len(CONSTRAINTS))
            for cypher in CONSTRAINTS:
                logger.info("  %s", cypher)
                await session.run(cypher)

            logger.info("--- Applying %d performance indexes ---", len(INDEXES))
            for cypher in INDEXES:
                logger.info("  %s", cypher)
                await session.run(cypher)

        logger.info("✅ All Neo4j constraints and indexes applied successfully.")
        await driver.close()
    except Exception as e:
        logger.error("❌ Failed to initialize Neo4j: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_neo4j())
