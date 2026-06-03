"""Add SS02 Memory Runtime tables

Revision ID: 001_add_memory_tables
Revises:
Create Date: 2026-05-17 10:00:00.000000

Schema: PostgreSQL 15+
Includes pgvector extension + HNSW indexes

Tables:
- episodic_memories (L2) — partitioned BY HASH (user_id) INTO 32
- fact_nodes (L3) — partitioned BY HASH (user_id) INTO 32
- identity_memories (L4) — not partitioned, replicated
- memory_encoding_events — partitioned BY RANGE (created_at)
- consolidation_jobs — not partitioned
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_add_memory_tables"
down_revision = "e814230ade46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ============================================================
    # L2: Episodic Memory (Partitioned BY HASH)
    # ============================================================
    op.execute(
        """
    CREATE TABLE episodic_memories (
        id UUID NOT NULL DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,

        episode_summary TEXT NOT NULL,
        episode_raw_turn_ids UUID[] NOT NULL,

        episode_start_at TIMESTAMP NOT NULL,
        episode_end_at TIMESTAMP NOT NULL,
        scene_context VARCHAR(100),

        emotional_peak JSONB NOT NULL,
        emotional_end JSONB NOT NULL,
        emotional_significance FLOAT NOT NULL CHECK (emotional_significance BETWEEN 0 AND 1),

        importance_score FLOAT NOT NULL CHECK (importance_score BETWEEN 0 AND 1),
        initial_importance FLOAT NOT NULL,
        decay_immunity FLOAT NOT NULL DEFAULT 0,
        state VARCHAR(20) NOT NULL CHECK (state IN ('vivid','fading','faint','dormant','archived')),

        last_recalled_at TIMESTAMP,
        recall_count BIGINT NOT NULL DEFAULT 0,
        reinforcement_history JSONB NOT NULL DEFAULT '[]'::jsonb,

        semantic_vector vector(768),
        emotional_vector vector(256),

        linked_episodes JSONB NOT NULL DEFAULT '[]'::jsonb,
        linked_facts JSONB NOT NULL DEFAULT '[]'::jsonb,

        reconstruction_hints JSONB NOT NULL DEFAULT '{}'::jsonb,

        do_not_recall BOOLEAN NOT NULL DEFAULT false,

        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        archived_at TIMESTAMP,

        PRIMARY KEY (id, user_id)
    ) PARTITION BY HASH (user_id)
    """
    )

    # Create 32 partitions for episodic_memories
    for i in range(32):
        op.execute(
            f"""
        CREATE TABLE episodic_memories_p{i} PARTITION OF episodic_memories
            FOR VALUES WITH (modulus 32, remainder {i})
        """
        )

    # Indexes on episodic_memories
    op.execute(
        """
    CREATE INDEX idx_episodic_user_recent
        ON episodic_memories (user_id, character_id, last_recalled_at DESC)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_episodic_user_importance
        ON episodic_memories (user_id, character_id, importance_score DESC)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_episodic_state
        ON episodic_memories (user_id, character_id, state)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_episodic_semantic
        ON episodic_memories USING hnsw (semantic_vector vector_cosine_ops)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_episodic_emotional
        ON episodic_memories USING hnsw (emotional_vector vector_cosine_ops)
    """
    )

    # ============================================================
    # L3: Semantic Memory (Partitioned BY HASH)
    # ============================================================
    op.execute(
        """
    CREATE TABLE fact_nodes (
        id UUID NOT NULL DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,

        predicate VARCHAR(100) NOT NULL,
        subject VARCHAR(100) NOT NULL,
        object TEXT NOT NULL,
        literal_text TEXT NOT NULL,

        raw_evidence TEXT NOT NULL,
        source_episode_ids UUID[] NOT NULL DEFAULT '{}',
        source_turn_ids UUID[] NOT NULL DEFAULT '{}',
        confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),

        emotional_charge FLOAT NOT NULL,
        emotional_label VARCHAR(30),

        importance FLOAT NOT NULL,
        is_identity_level BOOLEAN NOT NULL DEFAULT false,
        promoted_to_l4_at TIMESTAMP,
        promotion_reason TEXT,

        confirmation_count INT NOT NULL DEFAULT 0,
        contradiction_count INT NOT NULL DEFAULT 0,
        contradicting_fact_ids UUID[] NOT NULL DEFAULT '{}',
        is_corrected BOOLEAN NOT NULL DEFAULT false,
        do_not_recall BOOLEAN NOT NULL DEFAULT false,
        last_confirmed_at TIMESTAMP NOT NULL DEFAULT NOW(),
        last_contradicted_at TIMESTAMP,

        state VARCHAR(20) NOT NULL,

        related_facts JSONB NOT NULL DEFAULT '[]'::jsonb,

        semantic_vector vector(768),

        recall_count BIGINT NOT NULL DEFAULT 0,
        last_recalled_at TIMESTAMP,

        reconstruction_hints JSONB NOT NULL DEFAULT '{}'::jsonb,

        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

        PRIMARY KEY (id, user_id)
    ) PARTITION BY HASH (user_id)
    """
    )

    # Create 32 partitions for fact_nodes
    for i in range(32):
        op.execute(
            f"""
        CREATE TABLE fact_nodes_p{i} PARTITION OF fact_nodes
            FOR VALUES WITH (modulus 32, remainder {i})
        """
        )

    # Indexes on fact_nodes
    op.execute(
        """
    CREATE INDEX idx_fact_user_predicate
        ON fact_nodes (user_id, character_id, predicate)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_fact_user_importance
        ON fact_nodes (user_id, character_id, importance DESC)
        WHERE NOT do_not_recall
    """
    )
    op.execute(
        """
    CREATE INDEX idx_fact_semantic
        ON fact_nodes USING hnsw (semantic_vector vector_cosine_ops)
    """
    )

    # ============================================================
    # L4: Identity Memory (Sacred, not partitioned)
    # ============================================================
    op.execute(
        """
    CREATE TABLE identity_memories (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,

        category VARCHAR(50) NOT NULL,
        key VARCHAR(100) NOT NULL,
        value TEXT NOT NULL,

        disclosed_at TIMESTAMP NOT NULL,
        disclosure_context TEXT,
        source_episode_id UUID,
        source_turn_ids UUID[] NOT NULL DEFAULT '{}',

        sacred_reason TEXT NOT NULL,
        significance_score FLOAT NOT NULL CHECK (significance_score >= 0.85),
        promotion_trigger VARCHAR(50) NOT NULL,

        anniversary_pattern VARCHAR(20),
        next_anniversary_at TIMESTAMP,

        reconstruction_hints JSONB NOT NULL DEFAULT '{}'::jsonb,

        promoted_from_fact_id UUID,
        audit_log JSONB NOT NULL DEFAULT '[]'::jsonb,

        user_initiated_forget BOOLEAN NOT NULL DEFAULT false,
        forget_requested_at TIMESTAMP,

        created_at TIMESTAMP NOT NULL DEFAULT NOW(),

        UNIQUE (user_id, character_id, key)
    )
    """
    )

    # Indexes on identity_memories
    op.execute(
        """
    CREATE INDEX idx_l4_user
        ON identity_memories (user_id, character_id)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_l4_anniversary
        ON identity_memories (next_anniversary_at)
        WHERE next_anniversary_at IS NOT NULL
    """
    )

    # ============================================================
    # Encoding Events (Partitioned BY RANGE on created_at)
    # ============================================================
    op.execute(
        """
    CREATE TABLE memory_encoding_events (
        event_id UUID NOT NULL DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,
        source_turn_id UUID NOT NULL,
        source_user_text TEXT,
        source_assistant_text TEXT,
        recent_context JSONB,
        fast_signals JSONB,
        llm_extraction JSONB,
        status VARCHAR(20) NOT NULL,
        retry_count INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        llm_started_at TIMESTAMP,
        llm_completed_at TIMESTAMP,
        failed_at TIMESTAMP,
        failure_reason TEXT,

        PRIMARY KEY (event_id, created_at)
    ) PARTITION BY RANGE (created_at)
    """
    )

    # Create initial partition for current month (May 2026)
    op.execute(
        """
    CREATE TABLE memory_encoding_events_2026_05 PARTITION OF memory_encoding_events
        FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """
    )

    # Index on encoding events
    op.execute(
        """
    CREATE INDEX idx_encoding_status
        ON memory_encoding_events (status, created_at)
        WHERE status IN ('llm_pending', 'failed')
    """
    )

    # ============================================================
    # Consolidation Jobs (not partitioned)
    # ============================================================
    op.execute(
        """
    CREATE TABLE consolidation_jobs (
        job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,
        scheduled_for TIMESTAMP NOT NULL,
        pending_event_ids UUID[],
        turns_to_consolidate UUID[],
        episodes_created UUID[],
        facts_created UUID[],
        facts_reinforced UUID[],
        facts_contradicted UUID[],
        promotions_to_l4 UUID[],
        associations_created INT,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        duration_ms INT,
        failure_reason TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, character_id, scheduled_for)
    )
    """
    )

    # Index on consolidation jobs
    op.execute(
        """
    CREATE INDEX idx_consolidation_pending
        ON consolidation_jobs (scheduled_for, status)
        WHERE status = 'pending'
    """
    )


def downgrade() -> None:
    # Drop tables (automatically drops dependent indexes)
    op.execute("DROP TABLE IF EXISTS consolidation_jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS memory_encoding_events CASCADE")
    op.execute("DROP TABLE IF EXISTS identity_memories CASCADE")
    op.execute("DROP TABLE IF EXISTS fact_nodes CASCADE")
    op.execute("DROP TABLE IF EXISTS episodic_memories CASCADE")

    # Note: pgvector extension is kept to avoid issues with other tables
