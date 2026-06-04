# PARALLAX — TAIG Schema Specification
## Temporal Adversarial Intelligence Graph — Complete Design

---

## 1. Overview

TAIG is the **living knowledge graph** at the heart of PARALLAX. Every analyzed APK enriches it. Every query against it produces intelligence no single-APK tool can match.

This document is the **complete schema reference** for implementation.

---

## 2. Graph Architecture: Two-Graph Design

PARALLAX uses **two complementary stores**:

| Store | Tool | Content | Query Type |
|---|---|---|---|
| **Structural Graph** | Neo4j | Nodes, relationships, attribution, campaigns | Cypher traversal, pattern matching |
| **Semantic Vectors** | Qdrant | Code intent embeddings, UI embeddings | Cosine similarity, semantic search |

They stay synchronized: every Neo4j APK node has a Qdrant vector ID, and vice versa.

---

## 3. Neo4j Schema — Full Node Definitions

### 3.1 APK Node (Primary Entity)

```cypher
CREATE CONSTRAINT apk_sha256_unique IF NOT EXISTS
FOR (n:APK) REQUIRE n.sha256 IS UNIQUE;

CREATE INDEX apk_first_seen IF NOT EXISTS FOR (n:APK) ON (n.first_seen);
CREATE INDEX apk_risk_score IF NOT EXISTS FOR (n:APK) ON (n.risk_score);
CREATE INDEX apk_package IF NOT EXISTS FOR (n:APK) ON (n.package);
```

**Properties:**
```python
APK_PROPERTIES = {
    # Identity
    "sha256": str,           # primary key
    "md5": str,
    "package": str,          # e.g. "com.fake.sbi"
    "app_name": str,         # displayed name
    "version": str,
    "version_code": int,
    
    # Metadata
    "file_size": int,        # bytes
    "min_sdk": int,
    "target_sdk": int,
    "arch": str,             # "arm64-v8a"
    
    # Certificate
    "signer": str,
    "cert_fingerprint": str,
    "self_signed": bool,
    "cert_validity_days": int,
    
    # Analysis
    "first_seen": datetime,
    "last_analyzed": datetime,
    "analysis_count": int,
    "risk_score": int,       # 0-100
    "verdict": str,          # BENIGN | SUSPICIOUS | MALICIOUS | CRITICAL
    "confidence": float,     # 0.0-1.0
    
    # Source
    "submitted_by": str,
    "source": str,           # "api_upload", "honeypot", "misp", etc.
    
    # Static indicators
    "obfuscation_level": str,  # "none" | "low" | "medium" | "high"
    "packer": str,
    "anti_vm": bool,
    "anti_debug": bool,
    
    # Dynamic indicators
    "screenshot_count": int,
    "network_destinations": int,
    "frida_hooks_fired": int,
    
    # Visual
    "brand_impersonation_score": float,  # 0.0-1.0
    "phishing_overlay_detected": bool,
    
    # TAIG state
    "qdrant_vector_id": str,
    "campaign_id": str,      # if assigned
    "threat_actor_id": str,  # if attributed
}
```

---

### 3.2 Permission Node

```cypher
CREATE CONSTRAINT permission_name_unique IF NOT EXISTS
FOR (n:Permission) REQUIRE n.name IS UNIQUE;
```

```python
PERMISSION_PROPERTIES = {
    "name": str,                  # "android.permission.RECEIVE_SMS"
    "category": str,              # "sms" | "location" | "contacts" | "storage" | "phone" | "ui"
    "risk_level": str,            # "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    "protection_level": str,      # "normal" | "dangerous" | "signature" | "signatureOrSystem"
    "description": str,
    "common_malicious_use": str,  # known abuse patterns
}
```

---

### 3.3 API Call Node

```cypher
CREATE CONSTRAINT api_fqn_unique IF NOT EXISTS
FOR (n:API) REQUIRE n.fqn IS UNIQUE;
```

```python
API_PROPERTIES = {
    "fqn": str,             # "android.telephony.SmsManager.sendTextMessage"
    "class": str,           # "SmsManager"
    "package": str,         # "android.telephony"
    "method": str,          # "sendTextMessage"
    "sensitivity": str,     # "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    "attck_technique": str, # "T1412" if applicable
}
```

---

### 3.4 IPAddress Node

```cypher
CREATE CONSTRAINT ip_value_unique IF NOT EXISTS
FOR (n:IPAddress) REQUIRE n.value IS UNIQUE;
```

```python
IP_PROPERTIES = {
    "value": str,            # "185.220.101.47"
    "version": int,          # 4 or 6
    "country": str,          # ISO code
    "asn": str,              # "AS9009"
    "asn_org": str,
    "reputation": str,       # "malicious" | "suspicious" | "neutral" | "trusted"
    "first_seen_in_parallax": datetime,
    "last_seen": datetime,
    "observation_count": int,
    "tor_exit": bool,
    "vpn": bool,
    "hosting_provider": str,
}
```

---

### 3.5 Domain Node

```cypher
CREATE CONSTRAINT domain_fqdn_unique IF NOT EXISTS
FOR (n:Domain) REQUIRE n.fqdn IS UNIQUE;
```

```python
DOMAIN_PROPERTIES = {
    "fqdn": str,
    "tld": str,
    "registrar": str,
    "creation_date": date,
    "age_days": int,
    "dga_score": float,        # 0.0-1.0
    "ssl_issuer": str,
    "ssl_valid": bool,
    "ssl_self_signed": bool,
    "reputation": str,
    "first_seen_in_parallax": datetime,
    "observation_count": int,
}
```

---

### 3.6 Certificate Node

```cypher
CREATE CONSTRAINT cert_fingerprint_unique IF NOT EXISTS
FOR (n:Certificate) REQUIRE n.fingerprint IS UNIQUE;
```

```python
CERT_PROPERTIES = {
    "fingerprint": str,        # SHA-256 of cert
    "issuer_cn": str,
    "issuer_o": str,
    "subject_cn": str,
    "subject_o": str,
    "valid_from": date,
    "valid_to": date,
    "self_signed": bool,
    "key_algorithm": str,      # "RSA" | "ECDSA"
    "key_size": int,
    "signature_algorithm": str,
    "known_abuse": bool,       # if previously seen in malicious context
    "first_seen_in_parallax": datetime,
    "signs_apk_count": int,
}
```

---

### 3.7 ThreatActor Node

```cypher
CREATE CONSTRAINT actor_name_unique IF NOT EXISTS
FOR (n:ThreatActor) REQUIRE n.name IS UNIQUE;
```

```python
ACTOR_PROPERTIES = {
    "name": str,              # "GoldFactory"
    "aliases": list,          # ["GoldFactory APT", "GF-Group"]
    "origin": str,            # country/region attribution confidence
    "first_observed": date,
    "last_activity": date,
    "motivation": str,        # "financial" | "espionage" | "hacktivism" | "unknown"
    "ttps_summary": str,
    "active": bool,
    "sample_count": int,      # updated continuously
    "campaign_count": int,
}
```

---

### 3.8 Campaign Node

```cypher
CREATE CONSTRAINT campaign_name_unique IF NOT EXISTS
FOR (n:Campaign) REQUIRE n.name IS UNIQUE;
```

```python
CAMPAIGN_PROPERTIES = {
    "name": str,              # "SBI-YONO-2024-Q4"
    "start_date": date,
    "end_date": date,         # null if active
    "status": str,            # "active" | "dormant" | "concluded"
    "target_sector": str,     # "Banking" | "Healthcare" | "Government"
    "target_region": str,     # "IN" | "APAC" | "Global"
    "target_banks": list,     # ["State Bank of India", "HDFC"]
    "sample_count": int,
    "threat_actor": str,      # name reference
    "ttps_summary": str,
}
```

---

### 3.9 CodeBlob Node (Semantic Unit)

```cypher
CREATE CONSTRAINT blob_hash_unique IF NOT EXISTS
FOR (n:CodeBlob) REQUIRE n.hash IS UNIQUE;
```

```python
BLOB_PROPERTIES = {
    "hash": str,
    "semantic_vector": list,  # 768-dim, stored also in Qdrant
    "qdrant_point_id": str,
    "intent_label": str,      # "SMS_INTERCEPTION", "CREDENTIAL_OVERLAY", etc.
    "language": str,          # "java" | "smali" | "kotlin" | "native"
    "size_lines": int,
    "file_path": str,
    "apk_sha256": str,        # parent APK
}
```

---

### 3.10 BankApp Node (Target Reference)

```cypher
CREATE CONSTRAINT bankapp_package_unique IF NOT EXISTS
FOR (n:BankApp) REQUIRE n.package IS UNIQUE;
```

```python
BANKAPP_PROPERTIES = {
    "package": str,           # "com.sbi.lotus"
    "name": str,              # "SBI YONO"
    "bank": str,              # "State Bank of India"
    "country": str,
    "critical": bool,         # high-value target
    "user_count_millions": float,
    "play_store_url": str,
}
```

---

### 3.11 Supporting Nodes

```python
# Packer/Protector
PACKER_PROPERTIES = {
    "name": str,              # "DexGuard", "Allatori"
    "category": str,          # "obfuscator" | "packer" | "protector"
    "known_malicious": bool,
}

# FileResource (URLs, file paths in code)
RESOURCE_PROPERTIES = {
    "type": str,              # "url" | "filepath" | "ip"
    "value": str,
    "obfuscated": bool,
    "encrypted": bool,
}

# ATTCKTechnique (reference)
ATTCK_PROPERTIES = {
    "technique_id": str,      # "T1412"
    "name": str,
    "tactic": str,            # "Collection"
    "description": str,
    "url": str,               # MITRE URL
}

# Country
COUNTRY_PROPERTIES = {
    "code": str,              # "IN"
    "name": str,
}
```

---

## 4. Relationship Specifications

### 4.1 APK Relationships

```cypher
// Permissions
(apk:APK)-[:REQUESTS {
    first_seen: datetime,
    granted: bool
}]->(p:Permission)

// API calls
(apk:APK)-[:CALLS {
    call_count: int,
    methods_called: list
}]->(api:API)

// Network
(apk:APK)-[:COMMUNICATES_WITH {
    protocol: str,
    port: int,
    first_seen: datetime,
    data_size_bytes: int,
    encrypted: bool
}]->(ip:IPAddress)

(apk:APK)-[:COMMUNICATES_WITH {
    protocol: str,
    request_count: int
}]->(d:Domain)

// Brand impersonation
(apk:APK)-[:IMPERSONATES {
    confidence: float,
    method: str,  // "package_name" | "ui" | "icon" | "combined"
    evidence: str
}]->(b:BankApp)

// Certificate
(apk:APK)-[:SIGNED_BY {
    is_self_signed: bool
}]->(cert:Certificate)

// Packer usage
(apk:APK)-[:USES_PACKER]->(pkr:Packer)

// Binary similarity
(apk:APK)-[:SHARES_CODE_WITH {
    similarity: float,
    method: str,  // "BinDiff" | "Diaphora" | "embedding"
    code_blob_count: int
}]->(apk2:APK)

// Evolution
(apk:APK)-[:EVOLVED_FROM {
    generation: int,
    changes: str
}]->(apk2:APK)

// Attribution
(apk:APK)-[:ATTRIBUTED_TO {
    confidence: float,
    method: str,  // "infrastructure" | "code" | "ttps" | "combined"
    evidence: str
}]->(actor:ThreatActor)

// Campaign membership
(apk:APK)-[:PART_OF {
    role: str  // "initial" | "variant" | "pivot"
}]->(camp:Campaign)

// Targets
(apk:APK)-[:TARGETS_SECTOR]->(sector)
(apk:APK)-[:TARGETS_REGION]->(country)
(apk:APK)-[:TARGETS_BANK]->(bank:BankApp)

// Code composition
(apk:APK)-[:CONTAINS_BLOB]->(blob:CodeBlob)

// ATT&CK mapping
(apk:APK)-[:USES_TECHNIQUE {
    confidence: float,
    evidence: str
}]->(tech:ATTCKTechnique)

// Hardcoded resources
(apk:APK)-[:EMBEDS]->(r:FileResource)
```

### 4.2 Cross-Entity Relationships

```cypher
// Network infrastructure
(ip:IPAddress)-[:GEOLOCATES_TO]->(c:Country)
(d:Domain)-[:RESOLVES_TO]->(ip:IPAddress)
(d:Domain)-[:REGISTERED_WITH]->(registrar)

// Threat actor
(actor:ThreatActor)-[:CONDUCTS]->(camp:Campaign)
(camp:Campaign)-[:USES_INFRASTRUCTURE]->(ip:IPAddress)
(camp:Campaign)-[:USES_INFRASTRUCTURE]->(d:Domain)
(camp:Campaign)-[:ATTRIBUTED_TO {confidence: float}]->(actor)

// Certificate reuse
(cert:Certificate)-[:SIGNED_APKS {count: int}]->(apk:APK)

// Code blob lineage
(blob:CodeBlob)-[:VARIANT_OF {similarity: float}]->(blob2:CodeBlob)
(blob:CodeBlob)-[:FOUND_IN]->(apk:APK)
```

---

## 5. Pre-Built Threat Hunting Queries

### 5.1 Campaign Discovery

**Q: "All APKs targeting SBI in last 30 days sharing C2 infrastructure"**
```cypher
MATCH (a:APK)-[:IMPERSONATES]->(:BankApp {package: "com.sbi.lotus"})
MATCH (a)-[:COMMUNICATES_WITH]->(ip:IPAddress)<-[:COMMUNICATES_WITH]-(b:APK)
WHERE a.first_seen > datetime() - duration('P30D')
  AND a <> b
  AND b.risk_score >= 60
RETURN DISTINCT b.sha256 AS apk, b.package, b.risk_score, 
       collect(DISTINCT ip.value) AS shared_ips
ORDER BY b.risk_score DESC
```

### 5.2 Lineage Tracking

**Q: "Evolutionary lineage of current APK"**
```cypher
MATCH path = (root:APK)-[:EVOLVED_FROM*1..10]->(current:APK {sha256: $hash})
RETURN path, 
       length(path) AS generations_back,
       [n IN nodes(path) | n.sha256] AS lineage
ORDER BY generations_back DESC
LIMIT 1
```

### 5.3 Threat Actor Activity

**Q: "Top 10 active threat actors last 90 days"**
```cypher
MATCH (a:APK)-[:ATTRIBUTED_TO]->(actor:ThreatActor)
WHERE a.first_seen > datetime() - duration('P90D')
WITH actor, count(a) AS samples, 
     count(DISTINCT a.campaign_id) AS campaigns
RETURN actor.name, samples, campaigns,
       actor.motivation, actor.origin
ORDER BY samples DESC
LIMIT 10
```

### 5.4 Infrastructure Pivot Detection

**Q: "APKs sharing C2 IP with known-malicious samples"**
```cypher
MATCH (known:APK {verdict: "CRITICAL"})-[:COMMUNICATES_WITH]->(ip:IPAddress)
      <-[:COMMUNICATES_WITH]-(suspect:APK)
WHERE suspect.verdict IN ["SUSPICIOUS", "MALICIOUS", "CRITICAL"]
  AND known.first_seen < suspect.first_seen
RETURN suspect.sha256, suspect.package, suspect.risk_score,
       collect(DISTINCT known.sha256) AS linked_to_known,
       collect(DISTINCT ip.value) AS pivot_ips
ORDER BY suspect.risk_score DESC
```

### 5.5 Our Bank's Threat Landscape

**Q: "What's targeting our bank specifically in last 30 days"**
```cypher
MATCH (a:APK)-[:IMPERSONATES]->(b:BankApp {name: $our_bank_name})
WHERE a.first_seen > datetime() - duration('P30D')
OPTIONAL MATCH (a)-[:CALLS]->(api:API)
OPTIONAL MATCH (a)-[:ATTRIBUTED_TO]->(actor:ThreatActor)
OPTIONAL MATCH (a)-[:PART_OF]->(camp:Campaign)
RETURN a.sha256, a.package, a.risk_score, a.verdict,
       collect(DISTINCT api.attck_technique) AS techniques,
       collect(DISTINCT actor.name) AS actors,
       collect(DISTINCT camp.name) AS campaigns
ORDER BY a.risk_score DESC
```

### 5.6 Brand Protection (Most-Impersonated Bank)

**Q: "Which legitimate bank apps are most impersonated"**
```cypher
MATCH (a:APK)-[r:IMPERSONATES]->(b:BankApp)
WHERE a.risk_score >= 60
RETURN b.name, b.bank, b.country,
       count(a) AS impersonation_count,
       avg(r.confidence) AS avg_confidence
ORDER BY impersonation_count DESC
LIMIT 20
```

### 5.7 Cross-Campaign Infrastructure Reuse

**Q: "Two campaigns sharing infrastructure = actor pivot"**
```cypher
MATCH (c1:Campaign)-[:USES_INFRASTRUCTURE]->(infra)<-[:USES_INFRASTRUCTURE]-(c2:Campaign)
WHERE c1 <> c2
WITH c1, c2, collect(infra) AS shared
WHERE size(shared) >= 2
RETURN c1.name, c2.name, 
       [i IN shared | i.value] AS shared_infra
ORDER BY size(shared) DESC
```

### 5.8 Family Genealogy

**Q: "All code blobs found in this family, with variants"**
```cypher
MATCH (b:CodeBlob {intent_label: "SMS_INTERCEPTION"})
MATCH (b)<-[:CONTAINS_BLOB]-(apk:APK)
MATCH (b)-[:VARIANT_OF*0..5]-(related:CodeBlob)
RETURN apk.package, apk.risk_score,
       collect(DISTINCT related.intent_label) AS variant_intents
```

---

## 6. Vector Index (Qdrant) Specification

### 6.1 Collections

```python
COLLECTIONS = {
    "apk_intent": {
        "vector_size": 768,
        "distance": "Cosine",
        "payload_schema": ["sha256", "package", "risk_score", "intents"]
    },
    "code_blob": {
        "vector_size": 768,
        "distance": "Cosine",
        "payload_schema": ["blob_hash", "intent_label", "apk_sha256"]
    },
    "screenshot": {
        "vector_size": 1024,  # CLIP ViT-L/14
        "distance": "Cosine",
        "payload_schema": ["screenshot_id", "apk_sha256", "ui_description"]
    },
}
```

### 6.2 Indexing Pipeline

```python
# On new APK analysis complete
async def index_apk_vectors(apk_sha256: str, analysis_result: dict):
    # 1. APK-level intent vector (mean of blob vectors)
    apk_vector = np.mean([b.embedding for b in analysis_result.blobs], axis=0)
    await qdrant.upsert("apk_intent", [{
        "id": apk_sha256,
        "vector": apk_vector.tolist(),
        "payload": {
            "sha256": apk_sha256,
            "package": analysis_result.package,
            "risk_score": analysis_result.risk_score,
            "intents": [b.intent_label for b in analysis_result.blobs]
        }
    }])
    
    # 2. Per-blob vectors
    for blob in analysis_result.blobs:
        await qdrant.upsert("code_blob", [{
            "id": blob.hash,
            "vector": blob.embedding.tolist(),
            "payload": {
                "blob_hash": blob.hash,
                "intent_label": blob.intent_label,
                "apk_sha256": apk_sha256
            }
        }])
    
    # 3. Screenshot vectors
    for screenshot in analysis_result.screenshots:
        await qdrant.upsert("screenshot", [{
            "id": screenshot.id,
            "vector": screenshot.embedding.tolist(),
            "payload": {
                "screenshot_id": screenshot.id,
                "apk_sha256": apk_sha256,
                "ui_description": screenshot.llava_description
            }
        }])
```

### 6.3 Similarity Queries

```python
async def find_similar_apks(apk_sha256: str, k: int = 10):
    """Find APKs semantically similar to the given one."""
    apk_vector = await qdrant.retrieve("apk_intent", [apk_sha256])
    results = await qdrant.search(
        collection_name="apk_intent",
        query_vector=apk_vector,
        limit=k,
        score_threshold=0.7
    )
    return results
```

---

## 7. Graph Population Pipeline

### 7.1 Bootstrap (New APK)

```python
async def populate_apk_to_graph(analysis_result: AnalysisResult):
    async with neo4j_session() as session:
        # 1. Create APK node
        await session.run("""
            MERGE (a:APK {sha256: $sha256})
            SET a += $properties
        """, sha256=analysis_result.sha256, properties=...)
        
        # 2. Permissions
        for perm in analysis_result.permissions:
            await session.run("""
                MERGE (p:Permission {name: $name})
                SET p += $props
                WITH p
                MATCH (a:APK {sha256: $sha256})
                MERGE (a)-[r:REQUESTS]->(p)
                SET r.first_seen = $first_seen
            """, name=perm.name, props=perm.dict(), sha256=..., first_seen=...)
        
        # 3. APIs
        # 4. IPs and Domains
        # 5. Brand impersonation
        # 6. Certificate
        # 7. ATT&CK techniques
        # 8. Code blobs
        # ... (similar for all entity types)
```

### 7.2 Similarity Edge Creation (Post-Population)

```python
async def create_similarity_edges(new_apk_sha256: str):
    """After APK is in graph, find similar ones and create edges."""
    similar_apks = await find_similar_apks(new_apk_sha256, k=20, threshold=0.5)
    
    async with neo4j_session() as session:
        for similar in similar_apks:
            await session.run("""
                MATCH (a:APK {sha256: $new_sha256})
                MATCH (b:APK {sha256: $similar_sha256})
                MERGE (a)-[r:SHARES_CODE_WITH]->(b)
                SET r.similarity = $similarity,
                    r.method = 'embedding'
            """, new_sha256=new_apk_sha256,
                 similar_sha256=similar.sha256,
                 similarity=similar.score)
```

### 7.3 Campaign Detection (Periodic)

```python
async def detect_campaigns():
    """Run community detection periodically to identify new campaigns."""
    async with neo4j_session() as session:
        # Use Neo4j GDS library
        result = await session.run("""
            CALL gds.louvain.stream('apk-similarity-graph')
            YIELD nodeId, communityId
            RETURN gds.util.asNode(nodeId).sha256 AS sha256, communityId
        """)
        
        # Group by community
        communities = {}
        async for record in result:
            sha = record["sha256"]
            comm = record["communityId"]
            communities.setdefault(comm, []).append(sha)
        
        # For each community with 3+ APKs, create campaign node
        for comm_id, sha_list in communities.items():
            if len(sha_list) >= 3:
                await create_campaign_node(comm_id, sha_list)
```

---

## 8. Qdrant-to-Neo4j Consistency

Every APK appears in both stores with the same identifier:

```python
# On analysis complete
neo4j.create_apk_node(sha256, properties)
qdrant.upsert_vector("apk_intent", sha256, vector, payload)

# On delete (rare, but possible)
neo4j.delete_apk_node(sha256)
qdrant.delete_point("apk_intent", sha256)
```

**Reconciliation cron job** (daily) verifies both stores are in sync.

---

## 9. Performance Considerations

### 9.1 Indexes (Neo4j)

```cypher
// Property indexes
CREATE INDEX apk_first_seen IF NOT EXISTS FOR (n:APK) ON (n.first_seen);
CREATE INDEX apk_risk_score IF NOT EXISTS FOR (n:APK) ON (n.risk_score);
CREATE INDEX apk_package IF NOT EXISTS FOR (n:APK) ON (n.package);
CREATE INDEX apk_verdict IF NOT EXISTS FOR (n:APK) ON (n.verdict);

CREATE INDEX ip_country IF NOT EXISTS FOR (n:IPAddress) ON (n.country);
CREATE INDEX ip_reputation IF NOT EXISTS FOR (n:IPAddress) ON (n.reputation);

CREATE INDEX domain_age IF NOT EXISTS FOR (n:Domain) ON (n.age_days);
CREATE INDEX domain_reputation IF NOT EXISTS FOR (n:Domain) ON (n.reputation);

CREATE INDEX actor_active IF NOT EXISTS FOR (n:ThreatActor) ON (n.active);
CREATE INDEX campaign_status IF NOT EXISTS FOR (n:Campaign) ON (n.status);

// Composite indexes for common queries
CREATE INDEX apk_severity_date IF NOT EXISTS FOR (n:APK) ON (n.verdict, n.first_seen);
```

### 9.2 Graph Data Science Library

Used for:
- **Community detection** (Louvain, Label Propagation) → campaign discovery
- **Centrality** (PageRank) → most-important infrastructure
- **Similarity** (Node Similarity) → find related APKs
- **Path finding** → infrastructure chains

### 9.3 Scale Targets

| Metric | Target | How |
|---|---|---|
| Nodes | 10M+ | Neo4j scales horizontally with sharding; consider NebulaGraph for >100M |
| Edges | 100M+ | Same |
| Query latency (p95) | < 2 sec | Indexes + GDS precomputations |
| Bulk load | 10K APKs/hour | Periodic batch population |
| Real-time updates | 100 APKs/minute | Streaming pipeline |

---

## 10. Sample Cypher Query Library (Saved in Code)

```python
THREAT_HUNTING_QUERIES = {
    "find_campaign_by_ip": """
        MATCH (ip:IPAddress {value: $ip})
        MATCH (a:APK)-[:COMMUNICATES_WITH]->(ip)
        OPTIONAL MATCH (a)-[:PART_OF]->(c:Campaign)
        RETURN a, collect(DISTINCT c) AS campaigns
    """,
    
    "actor_evolution": """
        MATCH (a:ThreatActor {name: $actor})
        MATCH (a)<-[:ATTRIBUTED_TO]-(apk:APK)
        RETURN apk ORDER BY apk.first_seen
    """,
    
    "our_bank_threats_30d": """
        MATCH (a:APK)-[:IMPERSONATES]->(b:BankApp {name: $bank})
        WHERE a.first_seen > datetime() - duration('P30D')
        AND a.risk_score >= 50
        RETURN a ORDER BY a.risk_score DESC
    """,
    
    "infrastructure_pivot": """
        MATCH (c1:Campaign)-[:USES_INFRASTRUCTURE]->(i)
              <-[:USES_INFRASTRUCTURE]-(c2:Campaign)
        WHERE c1 <> c2
        RETURN c1, c2, collect(i) AS shared
    """,
    
    "top_ttps_active_campaigns": """
        MATCH (a:APK)-[:USES_TECHNIQUE]->(t:ATTCKTechnique)
        WHERE a.first_seen > datetime() - duration('P90D')
        RETURN t.technique_id, t.name, count(a) AS usage_count
        ORDER BY usage_count DESC LIMIT 20
    """,
    
    "yara_rule_effectiveness": """
        MATCH (a:APK)-[:DETECTED_BY]->(y:YARARule)
        RETURN y.name, count(a) AS detection_count
        ORDER BY detection_count DESC
    """,
}
```

---

## 11. MISP Integration Schema

PARALLAX auto-pushes to MISP in STIX 2.1 format:

```python
def create_misp_event(analysis_result) -> MISPEvent:
    event = MISPEvent()
    event.info = f"PARALLAX: {analysis_result.package} ({analysis_result.verdict})"
    event.threat_level_id = "1"  # HIGH
    event.analysis = "2"  # Completed
    event.distribution = "3"  # All communities (configurable)
    
    # Add IOCs
    for ip in analysis_result.ips:
        event.add_object("ip-port", ip=ip.value)
    
    for domain in analysis_result.domains:
        event.add_object("domain", value=domain.fqdn)
    
    for hash_type, hash_val in [("sha256", analysis_result.sha256),
                                  ("md5", analysis_result.md5)]:
        event.add_object("file", filename=analysis_result.package)
    
    # Add ATT&CK techniques as tags
    for tech in analysis_result.attck_techniques:
        event.add_tag(f"misp-galaxy:mitre-attack-pattern='{tech}'")
    
    return event
```

---

## 12. Backup & Recovery

- **Neo4j**: Daily full backup via `neo4j-admin dump`, retain 30 days
- **Qdrant**: Daily snapshot, retain 14 days
- **S3 (APKs, screenshots)**: Versioned bucket, retain 90 days for APKs, indefinite for evidence
- **Restore drill**: Quarterly

---

*This schema is the source of truth for TAIG implementation. Any schema changes require ADR (Architecture Decision Record).*
