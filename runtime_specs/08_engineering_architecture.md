# Subsystem 08: Engineering Architecture

> **Spec Version**: 1.0.0
> **Status**: Foundational / Tier 4 (Infrastructure)
> **Stability**: Schema changes require RFC
> **Subsystem Tag**: `[SS08]`
> **Implementation Owners**: Platform / Infra Team
> **作用**: 把 SS01-07 的所有设计落地到具体工程基础设施。是 Coding Agent 实施的依据。

---

## 1. 系统目标（System Purpose）

### 1.1 这个 subsystem 为什么存在

回答的核心问题：

> "前面 7 个 Subsystem 设计了'**逻辑层面**'。
> 但在**真实生产环境**下：
> - 这些服务**怎么部署**？
> - 用**什么数据库**？怎么 schema 设计？怎么 scaling？
> - 怎么**保证 100k DAU 不崩**？
> - **成本**控制在多少？
> - 怎么**监控、告警、调试**？
> - **数据合规**（GDPR / 隐私）怎么处理？
> - **多区域**部署如何设计？"

它存在的根本原因：

**这是给 Coding Agent (DeepSeek / Sonnet / 其他) 实施前面 7 个 Subsystem 的"落地手册"。**

### 1.2 它解决的根本问题

| 问题 | 当前 PRD 的做法 | 本 Subsystem 的做法 |
|------|---------------|---------------------|
| 部署 | "DigitalOcean Droplet + Docker Compose" | 完整 Kubernetes 多区域部署 + Service Mesh |
| 数据库 | PostgreSQL + Redis 单实例 | PG 主从 + 分片 + pgvector + 冷热分离 + S3 archive |
| Scaling | 不存在 | 从 1K → 1M DAU 的完整路径 |
| 成本 | "$42-47/月" (0 用户) | 详细 cost/MAU model + 优化路径 |
| 监控 | "Sentry 免费版" | 完整 Observability stack (Prometheus + OpenTelemetry + Loki) |
| 安全 | 不完整 | Auth + Encryption + Secrets + Audit + Compliance |
| 灾备 | 不存在 | RPO/RTO 定义 + 多区域 failover |
| Dev workflow | 不存在 | Local setup + Testing tiers + CI/CD |

### 1.3 在整个 Runtime 中的位置

```
┌──────────────────────────────────────────────────────────────┐
│                  Application Layer                           │
│  SS01 + SS02 + SS03 + SS04 + SS05 + SS06 + SS07              │
│  (前面 7 个 Subsystem)                                        │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ 依赖
                              ▼
┌──────────────────────────────────────────────────────────────┐
│           Subsystem 08: Engineering Architecture             │
│           (基础设施层 - 本 Subsystem)                          │
│                                                              │
│  - Service Topology (微服务 / 模块化单体)                     │
│  - Database Tier (PG + Redis + Qdrant + S3)                  │
│  - Event Bus (Redis Streams / Kafka)                         │
│  - LLM Provider Abstraction                                  │
│  - Caching Strategy                                          │
│  - Deployment (Kubernetes Multi-Region)                      │
│  - CI/CD Pipeline                                            │
│  - Observability Stack                                       │
│  - Security & Compliance                                     │
│  - Cost Management                                           │
│  - Disaster Recovery                                          │
└──────────────────────────────────────────────────────────────┘
```

### 1.4 依赖关系

```yaml
this_subsystem_depends_on:
  - 第三方服务：
    - Anthropic API (Claude)
    - DeepSeek API
    - OpenAI API (backup)
    - Cloud Provider (AWS / GCP / Aliyun)
    - LLM API
    - Push Notification (FCM / APNs)
    - Payment (Stripe / Lemon Squeezy)

subsystems_depending_on_this:
  - All of SS01-07 (作为部署/运行环境)
```

---

## 2. 核心设计原则（Core Design Principles）

### 2.1 不可违反的工程原则

| ID | 规则 | 违反后果 |
|----|------|---------|
| **E-1** | **12-factor app 严格遵守** | 部署、扩展困难 |
| **E-2** | **All cross-service 通信通过明确接口（RPC / Event Bus），不直接 DB 访问** | 紧耦合 |
| **E-3** | **Statefulness 严格隔离到 data tier** | Service 不能水平扩展 |
| **E-4** | **Secrets 不进入代码 / 镜像** | 安全事件 |
| **E-5** | **所有 LLM 调用必须经 Model Router（不直连 SDK）** | 不可观测、不可降级 |
| **E-6** | **所有 service 必须 idempotent on retry** | 数据不一致 |
| **E-7** | **DB schema 演化必须 backwards-compatible** | 部署不能滚动 |
| **E-8** | **Multi-tenancy 严格隔离 (user_id-based RLS)** | 隐私事故 |
| **E-9** | **所有用户数据 encryption at rest + in transit** | 合规风险 |
| **E-10** | **观测优先：metrics + traces + logs 三件套** | 不可调试 |
| **E-11** | **成本可观测到 per-user per-day** | 无法优化 |
| **E-12** | **Disaster recovery 经过定期演练** | 真出事时不可用 |

### 2.2 架构不变量

```
INV-E-1: ∀ service S, S 在 Kubernetes 中部署 (3+ replicas, multi-AZ)

INV-E-2: ∀ user data D, D 加密存储 + 加密传输 (TLS 1.3+)

INV-E-3: ∀ database table T, T 含 user_id column 必须有 RLS policy

INV-E-4: ∀ LLM call C, C 经过 Model Router (logging + circuit breaker)

INV-E-5: ∀ user request, P95 e2e latency < 3s (first byte)

INV-E-6: 跨区域 (US/EU/CN), data residency 严格遵守

INV-E-7: ∀ secret S, S 来自 KMS / Vault, 不在代码 / 镜像 / 环境变量中
```

### 2.3 工程禁忌

| 禁止 | 原因 |
|------|------|
| ❌ Sticky session (用户绑定到特定 instance) | 不能滚动部署 |
| ❌ Service 直接调用对方 DB | 紧耦合 |
| ❌ 在 prod 跑 `pg_dump` 当 backup | RPO 不够 |
| ❌ 共享 DB 给所有服务 | 单点故障 + scaling 困难 |
| ❌ 把 user PII 放 logs | GDPR / 隐私 |
| ❌ 在 prod 直接连 DB 调试 | 风险 |
| ❌ 不版本化的 secrets | 故障无法回滚 |
| ❌ 关键路径上的非幂等操作 | retry 灾难 |

### 2.4 演进原则

```
P-EV-1: 模块化单体 → 微服务（逐步迁移）
  MVP: 模块化单体 (8 个 SS 作为 Python module)
  V1: 关键服务 (LLM 调用、Memory Consolidation) 独立部署
  V2: 完整微服务

P-EV-2: 单区域 → 多区域
  MVP: US-East
  V1: + EU-West
  V2: + AP-Singapore + CN

P-EV-3: 自管 → 托管
  MVP: 自管 PG / Redis
  V1: 托管 (RDS / ElastiCache)
  V2: + 托管 LLM (Bedrock / Vertex)

P-EV-4: 单 LLM provider → 多 provider
  MVP: Anthropic 主
  V1: + DeepSeek (cheap)
  V2: + Self-hosted Companion-LLM
```

---

## 3. Runtime Architecture（部署架构）

### 3.1 整体拓扑

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT TIER                                    │
│   [iOS App]  [Android App]  [Web App]  [Future: Desktop / VR]          │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ HTTPS / WSS
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          EDGE TIER                                      │
│   ┌──────────────────────────────────────────────────────────────┐     │
│   │   CDN (Cloudflare) + DDoS Protection + WAF                   │     │
│   └────────────────────────────┬─────────────────────────────────┘     │
│                                │                                        │
│   ┌────────────────────────────▼─────────────────────────────────┐     │
│   │   API Gateway (Cloudflare Workers / AWS API Gateway)         │     │
│   │   - Rate limiting (per user / IP)                            │     │
│   │   - Auth (JWT validation)                                    │     │
│   │   - WebSocket upgrade                                        │     │
│   │   - Geo routing (US/EU/CN)                                   │     │
│   └────────────────────────────┬─────────────────────────────────┘     │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       APPLICATION TIER                                  │
│                       (Kubernetes Cluster)                              │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │   API Layer (FastAPI + Uvicorn)                            │       │
│   │   - Conversation API  - Auth API  - Account API            │       │
│   │   - Admin API         - Webhook handlers                    │       │
│   │   Replicas: 5-50 (autoscaled)                              │       │
│   └────────────────────┬───────────────────────────────────────┘       │
│                        │                                                │
│   ┌────────────────────▼───────────────────────────────────────┐       │
│   │   Orchestrator Service (SS07)                              │       │
│   │   - Sync hot path                                          │       │
│   │   - Trace coordination                                     │       │
│   │   Replicas: 5-50                                           │       │
│   └────────────────────┬───────────────────────────────────────┘       │
│                        │                                                │
│   ┌────────────────────┴───────────────────────────────────────┐       │
│   │   Subsystem Services (SS01-06)                             │       │
│   │   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │       │
│   │   │ SS01 │ │ SS02 │ │ SS03 │ │ SS04 │ │ SS05 │ │ SS06 │   │       │
│   │   │ Soul │ │Memory│ │Emo.  │ │Rel.  │ │Comp. │ │Inner │   │       │
│   │   └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘   │       │
│   │   Replicas: 3-30 each (autoscaled)                         │       │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │   Worker Pool (Async Tasks)                                │       │
│   │   - Memory Encoder Worker                                  │       │
│   │   - Memory Consolidator Worker (night)                     │       │
│   │   - Critic Agent Worker                                    │       │
│   │   - Wellbeing Monitor Worker                               │       │
│   │   - Inner Loop Scheduler Worker                            │       │
│   │   - Proactive Sender Worker                                │       │
│   │   - SS01 Drift Detector Worker                             │       │
│   │   Replicas: per-type 2-20                                  │       │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │   Specialized Workers                                      │       │
│   │   - LLM Embedding Service (BGE-M3, GPU)                    │       │
│   │   - ASR Service (Whisper, GPU)                             │       │
│   │   - TTS Service (Fish Audio / Edge TTS)                    │       │
│   │   - Live2D Renderer Service (V1.5+)                        │       │
│   └────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA TIER                                      │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │   PostgreSQL Cluster (主存储)                               │       │
│   │   - Primary (write)                                        │       │
│   │   - Read replicas (×2-3)                                   │       │
│   │   - Partitioning: BY HASH(user_id) × 16-32                 │       │
│   │   - Extensions: pgvector, pg_partman, pg_cron              │       │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │   Redis Cluster (缓存 + 事件总线)                            │       │
│   │   - Cache mode                                              │       │
│   │   - Streams (Event Bus MVP)                                │       │
│   │   - Sorted sets (Pending initiatives scheduling)           │       │
│   │   - Pub/Sub (Real-time notifications)                      │       │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │   Vector Store                                              │       │
│   │   MVP: pgvector (in PG)                                    │       │
│   │   V2: Qdrant cluster (large scale embedding)               │       │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │   Object Storage (S3 / R2)                                 │       │
│   │   - Cold memory archive (> 365 days)                       │       │
│   │   - Audio recordings (V1.5)                                │       │
│   │   - Soul Spec backups                                      │       │
│   │   - Conversation export (GDPR)                             │       │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │   ClickHouse (V2: Analytics + Long-term traces)            │       │
│   │   - composition_traces archive                              │       │
│   │   - User behavior analytics                                 │       │
│   └────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL SERVICES                                 │
│                                                                         │
│   [LLM Providers]      [Push]        [Payment]      [Email/SMS]        │
│   - Anthropic          - FCM         - Stripe       - SendGrid         │
│   - DeepSeek           - APNs        - Lemon Sqz    - Twilio           │
│   - OpenAI (backup)                                                    │
│                                                                         │
│   [Monitoring]         [Secrets]                                       │
│   - Prometheus         - AWS KMS / Vault                                │
│   - Grafana                                                            │
│   - Jaeger                                                              │
│   - Loki                                                                │
│   - PagerDuty                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Service Decomposition

```yaml
services:
  
  # ─── API Layer ───
  api-gateway:
    type: "stateless API"
    framework: FastAPI
    endpoints:
      - POST /api/chat/send
      - GET  /api/chat/history
      - POST /api/auth/*
      - POST /api/call/voice/start
      - POST /api/call/video/start
      - GET  /api/memory/facts
      - GET  /api/points/*
      - POST /api/account/*
    replicas: 5-50 (autoscale on CPU 70%)
    resources: {cpu: 1, memory: 1Gi}
  
  # ─── Orchestrator (SS07) ───
  orchestrator-service:
    type: "stateless"
    role: "Per-turn coordinator"
    replicas: 5-50
    resources: {cpu: 1, memory: 1Gi}
  
  # ─── Subsystem Services ───
  soul-service:           # SS01
    type: "stateless"
    replicas: 3-15
    resources: {cpu: 0.5, memory: 512Mi}
    
  memory-service:         # SS02
    type: "stateless"
    replicas: 5-30        # 较高 (retrieval heavy)
    resources: {cpu: 1, memory: 1Gi}
  
  emotion-service:        # SS03
    type: "stateless"
    replicas: 3-15
    resources: {cpu: 0.5, memory: 512Mi}
  
  relationship-service:   # SS04
    type: "stateless"
    replicas: 3-15
    resources: {cpu: 0.5, memory: 512Mi}
  
  composer-service:       # SS05
    type: "stateless"
    replicas: 5-30        # 较高 (核心 path)
    resources: {cpu: 1, memory: 1Gi}
  
  inner-state-service:    # SS06
    type: "stateless"
    replicas: 3-15
    resources: {cpu: 0.5, memory: 512Mi}
  
  # ─── Workers ───
  memory-encoder-worker:
    type: "queue consumer"
    replicas: 3-15
    resources: {cpu: 1, memory: 1Gi}
    
  memory-consolidator-worker:
    type: "scheduled (night)"
    replicas: 2-20 (scale up at night)
    resources: {cpu: 2, memory: 2Gi}
  
  inner-loop-worker:
    type: "scheduled (hourly + event)"
    replicas: 3-10
    resources: {cpu: 0.5, memory: 512Mi}
  
  critic-worker:
    type: "queue consumer (sampled)"
    replicas: 3-15
    resources: {cpu: 0.5, memory: 512Mi}
  
  wellbeing-monitor-worker:
    type: "event consumer"
    replicas: 2-10
    resources: {cpu: 0.5, memory: 512Mi}
  
  proactive-sender-worker:
    type: "scheduled (every 10s)"
    replicas: 2-5
    resources: {cpu: 0.5, memory: 512Mi}
  
  # ─── ML Services ───
  embedding-service:
    type: "GPU service"
    model: BGE-M3 self-hosted
    replicas: 2-8 (GPU autoscale)
    resources: {cpu: 4, memory: 16Gi, gpu: 1×A10}
  
  asr-service:           # V1
    type: "GPU service"
    model: Whisper Medium
    replicas: 1-5 (GPU autoscale)
    resources: {cpu: 4, memory: 8Gi, gpu: 1×A10}
  
  tts-service:           # V1
    type: "GPU service (or external)"
    primary: Fish Audio API (external)
    backup: Edge TTS (free, V0)
    
  live2d-renderer:       # V1.5
    type: "stateless"
    replicas: 2-10
    resources: {cpu: 1, memory: 1Gi}
```

### 3.3 Service Mesh (Optional, V2)

```yaml
service_mesh:
  V0_V1: 不需要 (replicas 少，K8s Service 足够)
  V2: Istio / Linkerd
  
  benefits:
    - mTLS between services
    - Circuit breaker as infra (除业务层 SS07 之外)
    - Distributed tracing 自动注入
    - Traffic shaping (canary)
```

### 3.4 Multi-Region Architecture

```yaml
region_strategy:
  
  MVP_phase: # 0-10k DAU
    region: AWS us-east-1
    data_residency: 全球用户数据在 US
    
  growth_phase: # 10k - 100k DAU
    primary: AWS us-east-1
    secondary: AWS eu-west-1
    data_residency: EU 用户数据在 EU (GDPR)
    routing: based on user.region
    
  scale_phase: # 100k+ DAU
    regions:
      - AWS us-east-1 (US users)
      - AWS eu-west-1 (EU users)
      - Aliyun cn-shanghai (CN users, separate setup)
      - AWS ap-southeast-1 (Asia users)
    cross_region: 严格隔离 (合规)
    
  active_active:
    架构: 每 region 独立部署 + 独立 DB
    user_routing: 注册时 lock region
    cross_region_migration: 用户主动申请 + 数据迁移流程
```

### 3.5 Real-time Communication

```yaml
realtime:
  websocket:
    purpose:
      - Streaming LLM response
      - Multi-device state sync
      - Push proactive messages
    server: FastAPI Uvicorn (with websockets)
    scaling: 
      - sticky session OR session affinity
      - Redis Pub/Sub for cross-instance messaging
    target_concurrent: 100k connections
    
  voice_video_call (V1.5+):
    protocol: WebRTC
    signaling: WebSocket
    media_server: 
      MVP: Direct peer-to-peer (经过 STUN)
      V2: TURN server (NAT 穿透差时)
      V3: SFU (selective forwarding for AI 介入)
```

---

## 4. State Model（数据层架构）

### 4.1 Data Tier Overview

```yaml
data_tier:
  
  postgresql_cluster:
    role: 主存储（事务、关系数据、向量）
    setup:
      primary: 1 instance, multi-AZ
      read_replicas: 2-3 (read-heavy queries)
      version: PG 15+
      extensions:
        - pgvector       # 向量
        - pg_partman     # 分区自动化
        - pg_cron        # 定时任务
        - pg_stat_statements  # 性能监控
    storage:
      MVP: 100GB SSD
      Growth: 1TB SSD
      Scale: 10TB+ NVMe (per region)
    backup:
      continuous: WAL archiving to S3
      snapshot: every 6h
      retention: 30 days hot + 1 year archive
      RPO: < 5 minutes
      RTO: < 1 hour
  
  redis_cluster:
    role: 缓存 + 事件总线 + 调度
    setup:
      MVP: single master (with replica)
      V1: cluster mode (3 master + 3 replica)
    persistence: AOF (every second)
    eviction: allkeys-lru
    storage: 32GB+ (RAM)
  
  vector_store:
    MVP: pgvector (在 PG 中)
    V1: 仍 pgvector (HNSW index)
    V2: Qdrant cluster (大规模)
    capacity: 
      MVP: 1M embeddings
      V2: 100M+ embeddings
  
  object_storage:
    provider: S3 (AWS) / R2 (Cloudflare) / OSS (Aliyun)
    buckets:
      - cold-memory-archive
      - audio-recordings   (V1.5)
      - soul-spec-versions
      - user-exports        (GDPR)
      - traces-archive      (V1)
    lifecycle:
      - hot: 30 days standard
      - warm: 90 days infrequent access
      - cold: 365 days glacier
  
  clickhouse (V2):
    role: 分析 + 长期 trace
    use_cases:
      - Composition trace archive
      - User behavior analytics
      - Aggregated metrics for ML
    setup:
      V2: 3-node cluster
```

### 4.2 Database Partitioning Strategy

```yaml
partitioning:
  
  by_user_hash:
    rationale: 用户级 isolation + 水平扩展
    tables:
      - soul_activation_states          (16 partitions)
      - episodic_memories               (32)
      - fact_nodes                      (32)
      - emotion_states                  (16)
      - relationship_states             (16)
      - inner_states                    (16)
      - sessions                        (16)
    
    partition_count:
      MVP: 16 (足够 10k DAU)
      Growth: 32-64
      Scale: 128+
  
  by_time_range:
    rationale: 时序数据 + 老数据可归档
    tables:
      - memory_encoding_events           (monthly)
      - soul_activation_events           (monthly)
      - emotion_events                   (monthly)
      - relationship_events              (monthly)
      - inner_loop_history               (monthly)
      - composition_traces               (monthly)
      - traces                           (monthly)
      - safety_classifications           (monthly)
    
    retention:
      hot: 30-90 days (in PG)
      archive: 1-3 years (in S3)
      legal: 7 years (for compliance, if applicable)
```

### 4.3 Cache Strategy (跨 Subsystem)

```yaml
cache_layers:
  
  layer_0_in_process:
    purpose: Immutable / config data
    contents:
      - Soul Spec (loaded at startup)
      - Stage config
      - Activity pool
      - Anti-pattern automaton
    eviction: never (deploy invalidates)
  
  layer_1_redis_hot:
    purpose: Per-user fast lookup
    contents:
      - Soul Activation State (1h TTL)
      - Emotion State (30s TTL)
      - Relationship State (5min TTL)
      - Inner State (1h TTL)
      - L4 Identity Memory (24h TTL)
      - Session (1h TTL)
    serialization: msgpack
    key_pattern: "{subsystem}:{user_id}:{character_id}"
  
  layer_2_redis_shared:
    purpose: Cross-user cacheable
    contents:
      - Safety classifications (by message_hash, 7 days)
      - Embedding cache (24h TTL)
      - LLM response cache (selective, 1h TTL)
  
  layer_3_postgresql:
    purpose: Source of truth
    when_to_query: cache miss
```

### 4.4 Encryption Strategy

```yaml
encryption:
  
  at_rest:
    postgres: 
      method: Transparent Data Encryption (TDE)
      provider: AWS KMS / GCP KMS
    redis:
      method: AOF encryption (V2)
    s3:
      method: SSE-KMS
    
  in_transit:
    client_to_edge: TLS 1.3 (强制)
    edge_to_service: TLS 1.3 (mTLS in V2 service mesh)
    service_to_db: TLS 1.3
    service_to_llm: TLS 1.3 (Anthropic SDK 默认)
  
  field_level (V2):
    sensitive_fields:
      - user.phone_number
      - user.email
      - L4.value (sacred disclosure)
    method: Application-level encryption + Envelope encryption
    key_management: AWS KMS / HashiCorp Vault
  
  e2e_encryption (V3):
    optional_feature: 用户付费解锁
    impact: 服务端无法读取消息（影响 Memory/Emotion 等功能）
    use_case: 极隐私需求
```

---

## 5. 数据结构（完整 Schema 索引）

### 5.1 全部 PG Tables 汇总

```yaml
postgres_tables:
  
  # ─── User & Auth ───
  - users
  - user_devices
  - user_sessions_jwt
  - user_consents (GDPR)
  - user_safety_flags
  
  # ─── Character & Soul (SS01) ───
  - characters
  - user_characters (binding)
  - soul_activation_states (partitioned by user_id)
  - soul_activation_events (partitioned by time)
  
  # ─── Memory (SS02) ───
  - episodic_memories (partitioned by user_id, with vector)
  - fact_nodes (partitioned by user_id, with vector)
  - identity_memories
  - memory_encoding_events (partitioned by time)
  - consolidation_jobs
  
  # ─── Emotion (SS03) ───
  - emotion_states (partitioned by user_id)
  - emotion_events (partitioned by time)
  
  # ─── Relationship (SS04) ───
  - relationship_states (partitioned by user_id)
  - relationship_events (partitioned by time)
  
  # ─── Inner State + Behavior (SS06) ───
  - inner_states (partitioned by user_id)
  - pending_initiatives
  - inner_loop_history (partitioned by time)
  
  # ─── Orchestration (SS07) ───
  - sessions (partitioned by user_id)
  - traces (partitioned by time)
  - wellbeing_states
  - safety_classifications
  - circuit_breaker_states
  - composition_traces (partitioned by time)
  - anti_pattern_violations
  - reroll_audit
  
  # ─── Conversation ───
  - messages (partitioned by user_id, with retention)
  
  # ─── Payment ───
  - points
  - points_transactions
  - subscriptions
  - payment_events
  
  # ─── Audit ───
  - audit_events (partitioned by time)
  - gdpr_requests
```

### 5.2 推荐 Indexing Strategy

```sql
-- 通用模式
CREATE INDEX idx_{table}_user_recent ON {table} (user_id, character_id, updated_at DESC);
CREATE INDEX idx_{table}_filter ON {table} (specific_filter_column) WHERE useful_predicate;

-- Vector indexes
CREATE INDEX idx_episodic_semantic ON episodic_memories 
    USING hnsw (semantic_vector vector_cosine_ops)
    WITH (m=16, ef_construction=128);

-- Partitioned tables
-- 每个 partition 单独 index 自动创建

-- Time-based queries
CREATE INDEX idx_events_recent ON {events_table} (created_at DESC) 
    WHERE created_at > NOW() - INTERVAL '30 days';
```

### 5.3 Migration Strategy

```yaml
migrations:
  tool: Alembic (Python) 或 Flyway
  
  rules:
    R-M-1: Migrations must be backwards-compatible
            (old code can still work on new schema)
    R-M-2: 大表加 column: 默认 NULL (避免 long table lock)
    R-M-3: 加 index: CONCURRENTLY (避免锁表)
    R-M-4: 删 column: 先 deprecate (注释 "deprecated") 1 release, 再 drop
    R-M-5: 改类型: 创建新 column, copy data, swap
  
  versioning:
    每次 migration → 单独 PR + review
    含 up + down (回滚) scripts
    在 staging 测试
    Production 灰度部署 (canary first)
  
  zero_downtime_deployment:
    1. 部署兼容新旧 schema 的代码
    2. 运行 migration (CONCURRENTLY)
    3. 部署使用新 schema 的代码
    4. (optional) 部署清理旧 schema 的代码
```

---

## 6. Prompt Runtime Integration

这个 subsystem 不直接参与 prompt composition。但提供以下 LLM 相关基础设施：

### 6.1 LLM Provider Abstraction

```python
# Common interface for all LLM providers

class LLMProvider(ABC):
    
    @abstractmethod
    async def stream(
        self, prompt: str, **params,
    ) -> AsyncIterator[str]: ...
    
    @abstractmethod
    async def call(
        self, prompt: str, **params,
    ) -> str: ...
    
    @abstractmethod
    def estimate_cost(self, prompt: str, params: dict) -> float: ...
    
    @abstractmethod
    def get_model_info(self) -> ModelInfo: ...

class AnthropicProvider(LLMProvider): ...
class DeepSeekProvider(LLMProvider): ...
class OpenAIProvider(LLMProvider): ...
class CompanionLLMProvider(LLMProvider):  # V2 self-hosted
    # vLLM endpoint
    ...
```

### 6.2 LLM Cost Tracking

```python
class LLMCostTracker:
    """
    每次 LLM call 后记录成本。
    """
    
    PRICING = {
        "claude-sonnet-4-6": {
            "input_per_1m": 3.00,
            "output_per_1m": 15.00,
        },
        "claude-haiku-4-5": {
            "input_per_1m": 0.80,
            "output_per_1m": 4.00,
        },
        "deepseek-v3": {
            "input_per_1m": 0.14,
            "output_per_1m": 0.28,
        },
        "gpt-4o": {
            "input_per_1m": 2.50,
            "output_per_1m": 10.00,
        },
        # V2: companion-llm-v2 self-hosted (摊销成本)
        "companion-llm-v2": {
            "input_per_1m": 0.50,  # amortized
            "output_per_1m": 1.00,
        },
    }
    
    async def record(self, call: LLMCall):
        cost = self._compute_cost(call)
        
        # Write to time-series store (Prometheus / ClickHouse)
        await self.metrics.observe(
            "llm.cost",
            cost,
            labels={
                "model": call.model,
                "user_id_bucket": self._bucket(call.user_id),
                "agent": call.agent_name,
            },
        )
        
        # Aggregate per user per day
        await self.user_cost_store.increment(
            call.user_id,
            cost,
            date=today(),
        )
        
        # Alert if user cost exceeds threshold
        if await self.user_cost_store.get_daily(call.user_id) > USER_DAILY_LIMIT:
            await self.alerts.notify("user.cost.exceeded", {...})
```

### 6.3 LLM Call Patterns

```yaml
llm_call_patterns:
  
  main_response:
    used_by: SS05 (主响应)
    model_tier: main_strong
    streaming: yes
    timeout: 30s
    retry: 0 (streaming 不重试，用 reroll)
    
  memory_encoding:
    used_by: SS02 Encoder Worker
    model_tier: cheap
    streaming: no
    json_mode: yes
    timeout: 10s
    retry: 2 (idempotent)
    batch: yes (V2)
    
  memory_consolidation:
    used_by: SS02 Consolidator Worker
    model_tier: cheap
    streaming: no
    timeout: 30s
    batch: yes
    
  safety_classification:
    used_by: SS07 Safety Agent
    model_tier: cheap
    streaming: no
    json_mode: yes
    timeout: 5s
    retry: 1
    cached: by message_hash
    
  critic_evaluation:
    used_by: SS07 Critic Agent
    model_tier: critic
    streaming: no
    json_mode: yes
    timeout: 5s
    sampling: 30%
    
  proactive_message:
    used_by: SS06 Proactive Generator
    model_tier: cheap
    streaming: no
    timeout: 5s
    via: Persona Composer (统一接口)
    
  embedding:
    used_by: SS02 Encoder + Retriever
    provider: self-hosted BGE-M3
    batch_size: 32
    cache: 24h
```

### 6.4 LLM Failover Strategy

```yaml
failover_config:
  
  main_strong:
    primary: claude-sonnet-4-6
    fallback_chain:
      - claude-opus-4-7  # 更贵但同 provider
      - gpt-4o           # 不同 provider
    health_check: every 30s, simple ping
    circuit_breaker:
      threshold: 5 failures in 60s
      open_duration: 60s
  
  cheap:
    primary: deepseek-v3
    fallback_chain:
      - claude-haiku-4-5
      - deepseek-chat
    health_check: every 60s
```

---

## 7. Agent Integration（基础设施服务接口）

### 7.1 Service Discovery

```yaml
service_discovery:
  MVP: Kubernetes DNS (内部)
  V2: + Consul (for cross-region service discovery)
  
  service_naming:
    - api-gateway.heart.svc.cluster.local
    - orchestrator-service.heart.svc.cluster.local
    - memory-service.heart.svc.cluster.local
    - ...
```

### 7.2 RPC 模式

```yaml
rpc_patterns:
  
  service_to_service:
    MVP: HTTP/REST (gRPC overkill at small scale)
    V1: gRPC (efficiency)
    
    protocols:
      - Bilateral TLS (mTLS in V2)
      - JSON / Protobuf
      - Tracing headers (W3C Trace Context)
      - Timeout headers
  
  service_to_external:
    pattern: SDK + circuit breaker + retry
```

### 7.3 Event Bus Integration

```yaml
event_bus_setup:
  
  MVP:
    backend: Redis Streams
    schema:
      - Topic per event type
      - Consumer groups per consumer service
      - At-least-once delivery
      - Idempotency keys
  
  V2:
    backend: Kafka (managed - AWS MSK / Confluent Cloud)
    schema_registry: Avro / JSON Schema
    
  monitoring:
    - Consumer lag (alert if > 60s for critical topics)
    - Delivery failure rate
    - Topic backlog size
```

---

## 8. Emotional Realism Constraints

本 subsystem 是基础设施，与情感真实性的直接关联较弱，但有几点关键：

### 8.1 性能与沉浸感

```
慢响应 → 用户感到角色"卡顿" → 出戏
  → 严格 P95 < 3s 强制

每秒能处理多少 turn → 决定用户高峰能否流畅使用
  → 必须有 autoscaling + load test
```

### 8.2 数据完整性与角色连续性

```
DB 一致性 → 角色"记忆"准确
  → ACID 严格保证 (PG)
  → 不在关键路径用 eventual consistency

跨 device 状态 → 角色无论在哪个设备都是"她"
  → Single source of truth in server
  → WebSocket sync
```

### 8.3 故障时的优雅降级

```
LLM 故障 → 不显示 "Error 500"
  → Fallback Soul-flavored response

DB 部分故障 → 不显示 "Service Unavailable"
  → 用 cached state + 部分功能降级
  → 用户感受到"她在思考"，不感受到系统故障
```

---

## 9. Failure Cases（基础设施失败模式）

### 9.1 单点故障

| 风险 | 影响 | 缓解 |
|------|------|------|
| **PG primary 故障** | 写入中断 | 自动 failover 到 standby (RDS Multi-AZ) |
| **Redis 故障** | Cache miss, 性能下降 | Replicas + Sentinel; 服务降级到直接 PG |
| **LLM provider 故障** | 所有响应失败 | Multi-provider failover (SS07 Model Router) |
| **某个 AZ 故障** | 部分用户 timeout | K8s 跨 AZ 调度 + load balancer |
| **某个 Service 全部 replicas down** | 该 service 不可用 | Circuit Breaker + Fallback (SS07) |
| **Event Bus partition** | 异步任务积压 | 监控 lag + replay capability |
| **CDN/Edge 故障** | 用户无法访问 | 多 CDN provider (主备) |

### 9.2 数据完整性风险

| 风险 | 缓解 |
|------|------|
| **Schema migration 失败 mid-deploy** | Backwards-compatible migrations + rollback ready |
| **Replica lag too large** | 监控 + alert; force read from primary if critical |
| **Backup corrupted** | 多份 backup + periodic restore test |
| **Vector index 损坏** | Reindex script ready + 用 sequential scan as fallback |
| **Partition full** | pg_partman 自动管理 + monitoring |

### 9.3 安全 / 合规风险

| 风险 | 缓解 |
|------|------|
| **数据泄漏** | At-rest + in-transit encryption + access control |
| **跨用户数据访问** | RLS + 单测 + audit |
| **GDPR 删除请求超时** | Cascade delete pipeline + audit |
| **Secrets 泄漏** | KMS + rotation + scan code |
| **DDoS** | Cloudflare + rate limiting + auto-scaling |
| **Underage user** | Age verification at signup + safety overrides |

### 9.4 成本失控

| 风险 | 缓解 |
|------|------|
| **LLM cost runaway (重度用户)** | Per-user daily cap + cooling-off |
| **Storage 爆炸** | Archive policy + cold storage tier |
| **Egress bandwidth** | CDN + WebSocket compression |
| **Cluster 过度 scale** | Autoscale max limits + alert if scaling > 2x expected |

### 9.5 长期运维风险

| 风险 | 缓解 |
|------|------|
| **依赖外部 LLM provider 涨价** | Multi-provider; Companion-LLM V2 reduces dependency |
| **K8s upgrade 破坏 service** | Test in staging + canary |
| **Schema 不可演化** | 设计时考虑 backwards compat + 持续 refactor |
| **Tech debt 累积** | Quarterly tech debt review + dedicated time |

---

## 10. Engineering Guidance（实施指引）

### 10.1 完整技术栈

```yaml
languages:
  backend: Python 3.11+
  frontend_mobile: Flutter 3.16+
  frontend_web: Next.js 15+ (React)
  
backend_frameworks:
  api: FastAPI 0.115+
  async: asyncio + uvicorn
  ORM: SQLAlchemy 2.0 + Alembic migrations

databases:
  primary: PostgreSQL 15+ with extensions
  cache: Redis 7+
  vector_MVP: pgvector
  vector_V2: Qdrant
  object: S3 / R2 / OSS
  analytics_V2: ClickHouse

llm_clients:
  anthropic: anthropic SDK (Python)
  openai: openai SDK
  deepseek: openai-compatible SDK
  self_hosted: vLLM endpoint client

ml_services:
  embedding: BGE-M3 (HuggingFace) on vLLM/TEI
  asr: faster-whisper
  tts: 
    MVP: Edge TTS
    V1: Fish Audio API
    V2: GPT-SoVITS self-hosted
  live2d: Cubism SDK

infrastructure:
  container: Docker
  orchestration: Kubernetes 1.28+
  service_mesh_V2: Istio
  ingress: nginx-ingress / Cloudflare
  
ci_cd:
  pipeline: GitHub Actions / GitLab CI
  registry: AWS ECR / GitHub Container Registry
  deploy: ArgoCD (GitOps)
  
observability:
  metrics: Prometheus + Grafana
  traces: OpenTelemetry → Jaeger
  logs: structlog → Loki
  errors: Sentry
  alerts: PagerDuty / OpsGenie

security:
  auth: JWT (RS256) + refresh token
  secrets: AWS KMS / HashiCorp Vault
  scanning: Snyk / Trivy
  WAF: Cloudflare WAF
```

### 10.2 部署清单（Kubernetes 示例）

```yaml
# orchestrator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator-service
  namespace: heart
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0  # zero downtime
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      containers:
      - name: orchestrator
        image: heart/orchestrator:v1.0.0
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: heart-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: heart-secrets
              key: redis-url
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: heart-secrets
              key: anthropic-api-key
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 15"]  # graceful shutdown
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: orchestrator
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator-service
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "30"
```

### 10.3 CI/CD Pipeline

```yaml
ci_cd_stages:
  
  on_pull_request:
    - lint (ruff / mypy)
    - unit_tests
    - integration_tests (with test PG/Redis)
    - schema_validation (Soul Spec / Stage config)
    - golden_dialogues_replay (SS01)
    - security_scan (Snyk)
    - build_docker_image (don't push)
  
  on_main_merge:
    - all_PR_checks
    - build_and_push_image
    - deploy_to_staging
    - smoke_tests (in staging)
    - e2e_tests (full conversation flow)
    
  on_tag (release):
    - canary_deploy_5_percent
    - monitor_canary_30_min (metrics + critic + drift)
    - if_healthy: full_deploy
    - else: rollback
  
  deployment_strategy:
    - blue_green (for breaking changes)
    - rolling_update (default)
    - canary (for risky changes)
```

### 10.4 Local Development Setup

```yaml
local_dev:
  
  prerequisites:
    - Docker Desktop
    - Python 3.11+
    - Node.js 20+ (frontend)
    - Flutter SDK (mobile)
  
  setup:
    1. clone repo
    2. cp .env.example .env (fill secrets locally)
    3. docker-compose up postgres redis  # data tier
    4. uv sync                            # Python deps
    5. alembic upgrade head               # apply migrations
    6. python -m heart.bootstrap          # load Soul Specs etc.
    7. uvicorn heart.api.main:app --reload  # start API
  
  docker_compose.yml:
    services:
      - postgres: postgres:15-alpine with pgvector
      - redis: redis:7-alpine
      - minio: S3-compatible local (optional)
      - llm-mock: mock LLM server (for tests without API cost)
  
  testing:
    - unit: pytest tests/unit
    - integration: pytest tests/integration (uses local PG/Redis)
    - golden: pytest tests/golden (uses real LLM, billed)
    - load: locust -f tests/load/turn.py
```

### 10.5 Cost Analysis

#### 10.5.1 Per-User Cost Breakdown (Target: $1.5/MAU)

```yaml
cost_per_MAU:
  
  # LLM (largest cost)
  llm_main_response:
    avg_turns_per_day: 30
    avg_input_tokens: 3000
    avg_output_tokens: 100
    model: claude-sonnet-4-6
    cost_per_day: 
      input: 30 × 3000 / 1M × $3.00 = $0.27
      output: 30 × 100 / 1M × $15 = $0.045
    cost_per_MAU: $0.315 × 1 = ~$9.45/MAU (but mostly not MAU)
    
    # Realistic: many users low engagement
    realistic_per_MAU: ~$1.00 (heavy users skew high)
  
  llm_cheap_calls:
    memory_encoding + safety + critic + proactive
    cost_per_MAU: ~$0.10
  
  llm_embedding:
    self-hosted, amortized
    cost_per_MAU: ~$0.05
  
  # Compute
  api_compute: ~$0.05/MAU
  background_workers: ~$0.05/MAU
  
  # Data
  postgres_storage: ~$0.05/MAU
  redis_storage: ~$0.02/MAU
  s3_storage: ~$0.01/MAU
  bandwidth: ~$0.03/MAU
  
  # External
  push_notifications: ~$0.005/MAU
  
  # Monitoring + Misc
  observability: ~$0.05/MAU
  
  ─────────────────────────────────────
  total_per_MAU: ~$1.50
  
  target_after_companion_llm_V2: ~$0.40/MAU  # 60% reduction
```

#### 10.5.2 Scaling Cost Projection

```yaml
scaling_costs:
  
  1k_DAU:
    monthly: ~$300
    primary_cost: LLM
    infra: $50/month (single PG, Redis)
  
  10k_DAU:
    monthly: ~$3000
    primary_cost: LLM (~$1500)
    infra: $500/month (PG multi-AZ, Redis cluster)
    
  100k_DAU:
    monthly: ~$30000
    primary_cost: LLM (~$15000)
    infra: $5000/month
    moves_to: Multi-region setup
    
  1M_DAU:
    monthly: ~$300000
    primary_cost: LLM (~$150000)
    BUT: Companion-LLM V2 已上线，LLM cost 减 60%
    realistic: ~$150000/month
    requires: 自管 LLM inference cluster + GPU
```

### 10.6 Observability 详细配置

```yaml
metrics_config:
  
  golden_signals_dashboard:
    panels:
      - end_to_end_latency_p95
      - llm_first_byte_p95
      - turn_failure_rate
      - llm_cost_per_hour
      - active_users_count
      - websocket_connections_active
  
  per_subsystem_dashboards:
    - SS01: anchor injections, drift rate, anti-pattern hits
    - SS02: retrieval latency, encoding queue depth, L4 size
    - SS03: emotion distribution, mood drift
    - SS04: stage distribution, transition count
    - SS05: composition latency, reroll rate
    - SS06: proactive sent count, ritual streak
    - SS07: critic failure rate, wellbeing alert count
  
  alerts:
    
    critical_paging:
      - p95_latency > 5s for 5min
      - api error_rate > 5% for 5min
      - db_replication_lag > 10s for 5min
      - wellbeing.suicide_risk.detected (immediate human)
      - cost_per_hour > 2x baseline
    
    warning_slack:
      - p95_latency > 3s for 10min
      - llm_circuit_breaker_open
      - reroll_rate > 5%
      - drift_score_avg > 0.4 (per character)
      - storage_usage > 80%
    
    info_dashboards:
      - daily cost report
      - retention dashboard
      - feature usage breakdown

logging_config:
  structured: JSON via structlog
  
  log_levels:
    production: INFO
    staging: DEBUG
  
  retention:
    hot (Loki): 7 days
    warm (S3): 30 days
    cold (Glacier): 1 year
    
  PII_scrubbing:
    - 自动 redact email / phone / IP from logs
    - User text only logged in DEBUG (not prod)

tracing_config:
  protocol: OpenTelemetry
  sampling: 
    production: 10% (cost control)
    + always: errors, slow requests (> 3s), critical paths
  retention: 7 days hot, archive 30 days
```

### 10.7 Security Architecture

```yaml
security:
  
  authentication:
    primary: JWT (RS256)
    refresh_token: rotated, single-use
    session_timeout: 30 days (rotating)
    
  authorization:
    user_isolation: 
      - RLS (Row-Level Security) on PG
      - All queries WHERE user_id = current_user
      - Admin queries via separate role
    api_scope: per-endpoint permission
    
  api_security:
    rate_limiting: 
      - Per-user: 60 turns/min
      - Per-IP: 200 req/min
      - Anonymous: 10 req/min
    csrf: CSRF tokens for state-changing operations
    cors: strict allowed origins
    waf: Cloudflare WAF
  
  secrets_management:
    storage: AWS KMS / HashiCorp Vault
    rotation: 
      - LLM API keys: monthly
      - DB passwords: quarterly
      - JWT signing keys: yearly
    access: per-service IAM role
  
  data_protection:
    pii_classification:
      - public: username, character_id
      - sensitive: email, phone, payment
      - confidential: L4 disclosures, conversation content
    
    encryption: see §4.4
    
    deletion (GDPR):
      - User request → process within 30 days
      - Cascade delete: all subsystems
      - Audit log retained 90 days (legally required)
      - Confirmation to user
    
    export (GDPR):
      - User request → 30 days
      - Provide all conversation history + L4 facts in JSON
      - Email to verified user
  
  vulnerability_management:
    - Dependabot auto PRs
    - Snyk scanning on PRs
    - Trivy scanning on container builds
    - Quarterly penetration tests
    
  incident_response:
    - On-call rotation
    - Runbooks for common incidents
    - Post-mortem culture (blameless)
    - SLA: critical < 1h, major < 4h
```

### 10.8 Compliance

```yaml
compliance:
  
  GDPR (EU users):
    - Consent at signup
    - Data export within 30 days
    - Deletion within 30 days
    - DPO contact
    - Data residency in EU region
  
  CCPA (California):
    - Similar to GDPR
    - Right to know / delete / opt-out
  
  China (if launching CN):
    - 网络安全法
    - 数据出境严格管控
    - 实名制 (V2 选项)
    - 内容审核
    - 独立部署 (Aliyun CN region)
  
  age_compliance:
    - COPPA: no users under 13
    - 17+ on App Store / Teen on Google Play
    - Age verification at signup
    - Wellbeing override for minors (V2)
  
  content_moderation:
    - Per-region moderation rules
    - Human review queue for PURPLE
    - Trust & Safety team
```

### 10.9 Disaster Recovery

```yaml
disaster_recovery:
  
  RPO (Recovery Point Objective):
    - User data: < 5 minutes
    - Configuration: < 1 hour
    - Logs: < 24 hours
  
  RTO (Recovery Time Objective):
    - Full service: < 4 hours
    - Critical path (response): < 1 hour
    - Read-only mode: < 30 minutes
  
  backup_strategy:
    postgres:
      - WAL streaming to S3 (continuous)
      - Full snapshot daily
      - Cross-region replicated
      - Test restore: monthly
    
    redis:
      - AOF every second
      - Daily snapshot to S3
    
    s3_data:
      - Cross-region replication
      - Versioning enabled
  
  failover_scenarios:
    
    primary_db_failure:
      - Auto failover to standby (< 60s)
      - Promote standby
      - Spin up new standby
      - User-perceived: brief errors then resume
    
    region_failure:
      - V2+: route traffic to secondary region
      - V0/V1: degraded mode (read-only) until restored
    
    llm_provider_outage:
      - Auto failover (SS07 Model Router)
      - Persona-preserving fallback
      - User-perceived: slightly different responses
    
    catastrophic_data_loss:
      - Restore from S3 backups (RTO < 4h)
      - Notify users
      - Possibly some recent data loss (within RPO)
  
  drills:
    - Quarterly disaster recovery drill
    - Tested in staging environment
    - Documented runbooks
    - Post-drill improvements
```

### 10.10 Performance Optimization Roadmap

```yaml
performance_roadmap:
  
  MVP (current):
    target_p95: 3s
    approach:
      - 单 region 部署
      - Caching layers established
      - HNSW vector index
      - Streaming LLM
      - Async cold path
  
  V1 (10k DAU):
    target_p95: 2.5s
    add:
      - Read replicas
      - Connection pooling (pgbouncer)
      - More aggressive caching
      - CDN for static assets
  
  V2 (100k DAU):
    target_p95: 2s
    add:
      - Multi-region with geo-routing
      - Companion-LLM (faster than Claude)
      - Qdrant for vector search
      - gRPC between services
  
  V3 (1M DAU):
    target_p95: 1.5s
    add:
      - Edge inference (Companion-LLM at edge)
      - Predictive caching (next likely response)
      - WebSocket binary protocol
      - 自管 GPU inference cluster
```

---

## 11. Future Scalability

### 11.1 Scaling to 1M DAU

```yaml
scaling_milestones:
  
  ─── MVP: 0-1k DAU ───
  infra: single region, modular monolith
  cost: ~$300/month
  team: 2-3 engineers
  
  ─── Growth: 1k-10k DAU ───
  infra: 
    - Microservices begin (LLM, Memory, Inner Loop)
    - Multi-AZ PG
    - Redis cluster
  cost: ~$3k/month
  team: 5-10 engineers
  
  ─── Scale: 10k-100k DAU ───
  infra:
    - Full microservices
    - Multi-region (US + EU)
    - 自管 embedding GPU
    - Companion-LLM V1 (LoRA)
  cost: ~$30k/month
  team: 20-30 engineers
  
  ─── Mass: 100k-1M DAU ───
  infra:
    - 多 region (4+)
    - Full Companion-LLM V2
    - 自管 GPU 推理集群
    - Edge inference
  cost: ~$150-300k/month
  team: 50-100 engineers
```

### 11.2 Companion-LLM Infrastructure

```yaml
companion_llm_infra:
  
  V1 (LoRA approach):
    - LoRA per character on top of base model
    - Hosting: Anthropic API with custom routing 
      OR self-hosted vLLM on H100 cluster
    - Training: 周度小规模 SFT
    
  V2 (Full fine-tuned):
    - Fine-tuned model per character group
    - Self-hosted inference on H100 cluster
    - Training infrastructure:
      - 数据准备 pipeline (来自 user interactions + critic feedback)
      - Training cluster (8-32 H100s for SFT)
      - Quarterly model updates
      - A/B testing framework
    - Inference:
      - 自管 vLLM on H100 / A100 cluster
      - Per-region deployment
      - Cost: ~$0.50/M tokens (amortized)
    
  V3 (E2E Voice-Speech):
    - Speech-to-Speech model
    - Required: 自管 GPU 集群
    - Sub-second voice latency
```

### 11.3 Multi-Region Detailed Plan

```yaml
multi_region_plan:
  
  V1 (10k DAU): US single region
  
  V2 (50k DAU): Add EU region
    - 触发: GDPR users 增加 / 延迟优化
    - Architecture:
      - 两个独立 K8s cluster
      - 独立 PG + Redis
      - 跨 region 通信仅限 admin
      - 用户注册时 lock region
    - Cost: ~2x infra (但 LLM 共享)
  
  V3 (200k DAU): Add Asia + CN
    - Architecture:
      - CN region 完全独立 (Aliyun, 合规)
      - Asia region (Singapore) 为 EN/Asia
    - Cost: ~3-4x infra
  
  user_migration:
    - 不主动 migrate (用户 lock region)
    - 用户主动申请 → 数据迁移 pipeline
    - 一次性收费
```

### 11.4 Data Tier Scaling

```yaml
data_scaling:
  
  postgres:
    current: 16 partitions, 100GB
    scaling:
      - 32 partitions at 100k DAU
      - 64 partitions at 500k DAU
      - 128+ at 1M DAU
    vertical_limit: i4i.metal (10TB)
    horizontal_limit: 几乎无限 (按 user_id 分片)
  
  redis:
    current: single (with replica)
    scaling:
      - Cluster (3 master 3 replica) at 10k DAU
      - 6 master 6 replica at 100k
      - Geo-distributed (V2)
  
  vector_store:
    MVP: pgvector inline
    V1: pgvector dedicated PG cluster
    V2: Qdrant cluster
      - 数据量 > 100M embeddings
      - 性能要求 > 1k QPS
  
  storage:
    cold_archive: S3 Glacier (cheap forever)
    hot_data: SSD (within PG)
```

### 11.5 Cost Optimization Roadmap

```yaml
cost_optimization:
  
  immediate_MVP:
    - Self-hosted embedding (BGE-M3)
    - DeepSeek for non-main calls
    - Aggressive caching
    Expected savings: 40% vs naive
  
  V1:
    - LoRA per character (reduce Sonnet usage)
    - Memory compression
    - Critic sampling (30%)
    Expected savings: additional 20%
  
  V2:
    - Companion-LLM replaces main LLM
    - 自管 embedding GPU
    - Cold storage tiering
    Expected savings: 60% on LLM cost
  
  V3:
    - Edge inference (latency + cost)
    - Federated learning
    - Optimal sharding
    Expected savings: 30% on infra
```

### 11.6 Team Structure Evolution

```yaml
team_structure:
  
  MVP (5 people):
    - Tech Lead / CTO
    - 2 backend engineers
    - 1 frontend / mobile
    - 1 product / design
  
  V1 (15 people):
    - + ML engineer
    - + DevOps / SRE
    - + Content team (2)
    - + QA
    - + 1 more backend
  
  V2 (50+ people):
    - Multiple feature teams
    - Dedicated ML team (training Companion-LLM)
    - Dedicated SRE team
    - Trust & Safety team
    - Customer support
  
  V3 (100+):
    - Multi-region teams
    - Research team (Speech-to-Speech, etc.)
    - Compliance team
```

---

# 附录 A: 完整 Tech Stack Manifest

```yaml
# 完整技术栈清单 - 用于 Coding Agent 实施依据

backend:
  language: Python 3.11+
  
  frameworks:
    api: FastAPI 0.115+
    async_runtime: asyncio + uvicorn 0.30+
    
  libraries:
    db_orm: SQLAlchemy 2.0+ + asyncpg
    db_migration: Alembic
    validation: Pydantic 2.x
    
    redis_client: redis-py with asyncio
    
    llm_clients:
      - anthropic
      - openai (for OpenAI-compatible APIs like DeepSeek)
    
    embedding:
      - sentence-transformers (BGE-M3)
      - or via vLLM HTTP client
    
    background_tasks:
      MVP: asyncio.create_task
      V1: APScheduler
      V2: Celery / Temporal
    
    event_bus:
      MVP: redis-py Streams
      V2: confluent-kafka-python
    
    pattern_matching:
      - re (built-in)
      - pyahocorasick (multi-pattern Aho-Corasick)
    
    observability:
      - prometheus_client
      - opentelemetry-api / opentelemetry-sdk
      - structlog
    
    testing:
      - pytest + pytest-asyncio
      - locust (load testing)
      - hypothesis (property-based)

frontend_mobile:
  framework: Flutter 3.16+
  state: Provider 6.x
  http: dio
  websocket: web_socket_channel
  audio: just_audio + record
  live2d: cubism_sdk_for_flutter

frontend_web (V1+):
  framework: Next.js 15+
  styling: TailwindCSS 4.x
  ui: Ant Design 5.x or shadcn/ui
  state: Zustand
  websocket: socket.io-client

databases:
  postgresql:
    version: 15+
    extensions:
      - pgvector 0.7+
      - pg_partman
      - pg_cron
      - pg_stat_statements
    
  redis:
    version: 7+
    modules: 默认即可
    
  qdrant (V2):
    deployment: Helm chart on K8s

infrastructure:
  container_runtime: Docker / containerd
  orchestration: Kubernetes 1.28+
  ingress: nginx-ingress / Traefik / Cloudflare
  service_mesh_V2: Istio
  
  ci_cd:
    pipeline: GitHub Actions
    image_registry: AWS ECR / GitHub Container Registry
    deploy: ArgoCD
  
  observability:
    metrics: Prometheus + Grafana
    traces: Jaeger (via OpenTelemetry)
    logs: Loki
    errors: Sentry
    alerts: PagerDuty
  
  secrets: AWS KMS + AWS Secrets Manager (or Vault)
  
  cdn: Cloudflare
  
external_services:
  llm:
    - Anthropic API (Claude)
    - DeepSeek API
    - OpenAI API (backup)
  
  push:
    - Firebase Cloud Messaging (Android)
    - Apple Push Notification service (iOS)
  
  payment:
    - Stripe
    - Lemon Squeezy
  
  tts (V1):
    - Fish Audio
    - or self-hosted GPT-SoVITS
  
  asr:
    - faster-whisper (self-hosted)
```

---

# 附录 B: Phased Implementation Roadmap

```yaml
phased_roadmap:
  
  ─── Phase 0: Foundation (Week 1-4) ───
  goal: 把工程基础设施搭好
  deliverables:
    - K8s cluster setup
    - PG + Redis 运行
    - CI/CD pipeline
    - Basic auth + user API
    - Empty service skeletons for SS01-07
  
  ─── Phase 1: Soul + Memory Core (Week 5-12) ───
  goal: SS01 + SS02 完整实现
  deliverables:
    - Soul Spec system (Anchor, Drift Detector)
    - Memory L1-L4 full implementation
    - Memory encoding + retrieval + consolidation
    - 2 角色 (Rin + Dorothy) Soul Specs
    - Golden dialogues regression
  
  ─── Phase 2: Emotion + Relationship (Week 13-18) ───
  goal: SS03 + SS04 完整实现
  deliverables:
    - VAD emotion + active stack
    - Stage transitions + behavioral envelope
    - Conflict/repair mechanics
    - Reunion state machine
  
  ─── Phase 3: Composer + Inner State (Week 19-24) ───
  goal: SS05 + SS06 完整实现
  deliverables:
    - Persona Composer with all layers
    - Anti-pattern filter (streaming compatible)
    - Inner Loop scheduler
    - Proactive message system
    - Anniversary tracker
  
  ─── Phase 4: Orchestration + Safety (Week 25-30) ───
  goal: SS07 完整实现
  deliverables:
    - Orchestrator Agent
    - Safety Agent (5 levels)
    - Critic Agent with drift feedback
    - Director Agent
    - Wellbeing Monitor
    - Model Router with failover
  
  ─── Phase 5: Beta Launch (Week 31-36) ───
  goal: Closed beta with 100 users
  deliverables:
    - All 7 subsystems integrated
    - Mobile app (Flutter)
    - Basic monitoring + alerts
    - User feedback channel
    - Quick iteration
  
  ─── Phase 6: V1 Launch (Week 37-44) ───
  goal: Public launch with full features
  deliverables:
    - Voice calling (V1)
    - Multi-region (US + EU)
    - Cost optimization
    - Companion-LLM V1 (LoRA)
    - Compliance ready
  
  ─── V2+ ───
  - Video calling (Live2D)
  - Companion-LLM V2 (full fine-tune)
  - More characters
  - UGC workshop
  - Mass scale infrastructure
```

---

# 附录 C: 关键架构决策记录 (ADRs)

```markdown
# ADR-001: 模块化单体 vs 微服务

Status: Accepted (MVP), Plan to evolve

Context:
  - 团队小 (5 人)
  - 需要快速迭代
  - 但架构必须支持未来 scale

Decision:
  MVP 用模块化单体 (8 个 module = 8 个 subsystem)
  V1 拆分关键 services (LLM, Memory)
  V2 完整微服务

Consequences:
  + 快速迭代 (MVP)
  + 简单调试
  - 需要预留未来拆分的接口


# ADR-002: PostgreSQL 作为唯一主存储

Status: Accepted

Context:
  - 需要事务、关系、向量、JSON 多种支持
  - 简化运维

Decision:
  全部用 PG (with pgvector for vector, JSONB for unstructured)
  V2 必要时拆出 Qdrant

Consequences:
  + 单一 DB 简化
  + ACID 保证
  - pgvector 性能上限 (V2 时需要 migrate)


# ADR-003: Event Bus 用 Redis Streams (MVP)

Status: Accepted

Context:
  - 需要 async 任务调度 + 事件分发
  - 不想引入 Kafka (运维复杂)

Decision:
  MVP: Redis Streams
  V2: 迁移到 Kafka 当 throughput 需要

Consequences:
  + 简单 (Redis 已经有)
  - Throughput 有上限
  - 跨 region 复杂


# ADR-004: Companion-LLM 路线

Status: Planned

Context:
  - LLM 是最大成本
  - 通用模型不够细腻
  - 数据飞轮是长期护城河

Decision:
  V0-V1: 通用 LLM (Sonnet) + 复杂 prompt
  V1.5: LoRA per character on Sonnet
  V2: 自训 Companion-LLM (full fine-tune)

Consequences:
  + 长期 60% 成本下降
  + 角色一致性提升
  - 训练 + 部署成本前期高
  - 需要 ML 团队


# ADR-005: Multi-Region 触发条件

Status: Planned

Context:
  - GDPR 要求 EU 数据在 EU
  - 全球用户延迟要求

Decision:
  10k DAU OR EU 用户 > 1000 → 部署 EU region
  100k DAU OR CN 用户 > 5000 → 部署 CN region

Consequences:
  + 合规
  + 延迟改善
  - 运维复杂度 2-3x
  - 跨 region 严格隔离 (用户 lock region)
```

---

# 附录 D: 项目目录结构（推荐）

```
heart/
├── backend/
│   ├── heart/
│   │   ├── __init__.py
│   │   ├── api/                    # FastAPI endpoints
│   │   │   ├── main.py
│   │   │   ├── auth.py
│   │   │   ├── conversation.py
│   │   │   ├── memory.py
│   │   │   ├── points.py
│   │   │   └── admin.py
│   │   │
│   │   ├── ss01_soul/              # Subsystem 01
│   │   │   ├── registry.py
│   │   │   ├── activation_state.py
│   │   │   ├── anchor_injector.py
│   │   │   ├── drift_detector.py
│   │   │   ├── resonance_tracker.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── ss02_memory/            # Subsystem 02
│   │   │   ├── service.py
│   │   │   ├── encoder.py
│   │   │   ├── consolidator.py
│   │   │   ├── retriever.py
│   │   │   ├── reconstructor.py
│   │   │   ├── decay_engine.py
│   │   │   ├── reinforcer.py
│   │   │   ├── forgetting_affect.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── ss03_emotion/           # Subsystem 03
│   │   │   ├── service.py
│   │   │   ├── trigger_detector.py
│   │   │   ├── contagion.py
│   │   │   ├── decay.py
│   │   │   ├── mood_drift.py
│   │   │   ├── repair_detector.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── ss04_relationship/      # Subsystem 04
│   │   │   ├── service.py
│   │   │   ├── phase_engine.py
│   │   │   ├── trust_tracker.py
│   │   │   ├── attachment_tracker.py
│   │   │   ├── intimacy_calculator.py
│   │   │   ├── reunion_machine.py
│   │   │   ├── cold_war_tracker.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── ss05_composer/          # Subsystem 05
│   │   │   ├── service.py
│   │   │   ├── layer_aggregator.py
│   │   │   ├── conflict_resolver.py
│   │   │   ├── budget_allocator.py
│   │   │   ├── modality_adapter.py
│   │   │   ├── composer.py
│   │   │   ├── anti_pattern_filter.py
│   │   │   ├── streaming_filter.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── ss06_inner_state/       # Subsystem 06
│   │   │   ├── service.py
│   │   │   ├── inner_loop.py
│   │   │   ├── activity_generator.py
│   │   │   ├── concerns_tracker.py
│   │   │   ├── initiative_decider.py
│   │   │   ├── proactive_generator.py
│   │   │   ├── proactive_sender.py
│   │   │   ├── anniversary_tracker.py
│   │   │   ├── ritual_manager.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── ss07_orchestration/     # Subsystem 07
│   │   │   ├── orchestrator.py
│   │   │   ├── safety_agent.py
│   │   │   ├── critic_agent.py
│   │   │   ├── director_agent.py
│   │   │   ├── wellbeing_monitor.py
│   │   │   ├── model_router.py
│   │   │   ├── session_manager.py
│   │   │   ├── failure_handler.py
│   │   │   ├── event_bus.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── infra/                  # Subsystem 08 (本)
│   │   │   ├── db.py
│   │   │   ├── redis_client.py
│   │   │   ├── llm_providers/
│   │   │   │   ├── anthropic.py
│   │   │   │   ├── deepseek.py
│   │   │   │   ├── openai.py
│   │   │   │   └── self_hosted.py
│   │   │   ├── llm_cost_tracker.py
│   │   │   ├── circuit_breaker.py
│   │   │   ├── tracing.py
│   │   │   └── metrics.py
│   │   │
│   │   ├── workers/                # Async workers
│   │   │   ├── memory_encoder.py
│   │   │   ├── memory_consolidator.py
│   │   │   ├── inner_loop_scheduler.py
│   │   │   ├── critic_worker.py
│   │   │   ├── wellbeing_worker.py
│   │   │   └── proactive_sender.py
│   │   │
│   │   ├── safety/                 # Cross-cutting safety
│   │   │   ├── classifier.py
│   │   │   ├── care_path.py
│   │   │   └── keywords.py
│   │   │
│   │   └── utils/
│   │       ├── trace.py
│   │       ├── ids.py
│   │       └── time.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── golden/                 # Golden dialogues per character
│   │   └── load/
│   │
│   ├── migrations/                 # Alembic
│   ├── scripts/
│   ├── pyproject.toml
│   └── README.md
│
├── frontend_mobile/                # Flutter
│   └── (per Flutter project structure)
│
├── frontend_web/                   # Next.js (V1+)
│   └── (per Next.js project structure)
│
├── soul_specs/                     # YAML files (SS01)
│   ├── _schema.json
│   ├── rin/
│   │   └── v1.0.0.yaml
│   └── dorothy/
│       └── v1.0.0.yaml
│
├── config/
│   ├── stages.yaml                 # SS04 config
│   ├── emotion_decay.yaml          # SS03 config
│   ├── safety_keywords.yaml        # SS07 config
│   └── activity_pools/             # SS06 config
│
├── infra/                          # IaC
│   ├── kubernetes/
│   ├── terraform/
│   └── helm-charts/
│
├── runtime_specs/                  # ← 本系列文档
│   ├── README.md
│   ├── 00_runtime_worldview.md
│   ├── 01_identity_anchor_soul_spec.md
│   ├── 02_memory_runtime.md
│   ├── 03_emotion_state_machine.md
│   ├── 04_relationship_phase_engine.md
│   ├── 05_persona_composition_runtime.md
│   ├── 06_inner_state_behavior_runtime.md
│   ├── 07_agent_orchestration.md
│   └── 08_engineering_architecture.md
│
├── docs/                           # 其他文档
│   ├── api/
│   ├── runbooks/
│   ├── adrs/
│   └── onboarding.md
│
├── docker-compose.yml              # Local dev
├── .env.example
└── README.md
```

---

# 附录 E: 给 Coding Agent 的实施指引

```markdown
# 给 DeepSeek / Sonnet / 其他 Coding Agent 的实施指引

## 任务: 实施心屿 AI Companion 系统

## 阅读顺序 (强制)

1. /runtime_specs/README.md
2. /runtime_specs/00_runtime_worldview.md
3. 当前要实现的 Subsystem 文档 (01-08)
4. 依赖的 Subsystem 文档的 §1, §2, §5, §6, §7

## 实施原则

1. 严格遵守每个 Subsystem 的 P-N / INV-N / RULE 规则
2. 数据结构按 §5 Schema 严格实现
3. 性能符合 §10 targets
4. 测试通过 §11 fixtures + golden_dialogues
5. 每个 PR 包含:
   - 实现代码
   - 单元测试
   - 集成测试
   - Metrics + tracing
   - 文档更新 (if any)

## 不允许的实施自由

❌ 增加 Soul Spec 字段 (必须 RFC)
❌ 跳过 Anti-Pattern Filter
❌ 跨 user 读取数据
❌ 用 main LLM 做 cheap 任务 (cost)
❌ 同步等待 async 操作
❌ 删除任何 L4 memory
❌ 让用户感知到任何"系统术语" (immersion)

## 实施前检查清单

- [ ] 我已经读完 README + Worldview
- [ ] 我已经读完目标 Subsystem 完整 spec
- [ ] 我已经读完依赖 Subsystems 的接口部分
- [ ] 我理解 §2 设计原则
- [ ] 我理解 §6 / §7 与其他 Subsystem 的协作
- [ ] 我已查看 §11 测试 fixtures 和 golden tests

## 实施过程检查清单

- [ ] 严格按 §5 Schema 设计数据结构
- [ ] 数据库 schema 含 user_id RLS
- [ ] 所有 LLM 调用通过 Model Router
- [ ] 实现 §10 Engineering Guidance 的 service interfaces
- [ ] 添加 §10 列出的 metrics 和 traces
- [ ] 单元测试 + 集成测试

## PR 合入检查清单

- [ ] CI 全绿
- [ ] Golden tests 通过
- [ ] 性能符合 §10 targets
- [ ] Code review (至少 1 approval)
- [ ] 文档与代码一致
```

---

**End of Subsystem 08 Spec**

---

# 🎉 完整 Runtime Specification 系列已完成

```
✅ 00 - Runtime Worldview         (整体世界观)
✅ 01 - Identity Anchor + Soul Spec  (灵魂层)
✅ 02 - Memory Runtime              (记忆认知系统)
✅ 03 - Emotion State Machine       (情绪状态机)
✅ 04 - Relationship Phase Engine   (关系阶段引擎)
✅ 05 - Persona Composition Runtime (人格合成 - prompt 指挥家)
✅ 06 - Inner State + Behavior      (内心循环 + 主动行为)
✅ 07 - Agent Orchestration          (系统总指挥)
✅ 08 - Engineering Architecture     (工程落地)
```

下一步建议: 基于这套 spec 开始 **Phase 0 - Foundation** 实施。
