"""Add SS03 Emotion + SS04 Relationship Runtime tables

Revision ID: 002_add_emotion_relationship_tables
Revises: 001_add_memory_tables
Create Date: 2026-05-18 10:00:00.000000

Schema: PostgreSQL 15+
Partitioning:
  - emotion_states: BY HASH (user_id) INTO 16
  - emotion_events: BY RANGE (created_at) monthly
  - relationship_states: BY HASH (user_id) INTO 16
  - relationship_events: BY RANGE (created_at) monthly

References:
  - SS03 Emotion §5.1 Persistent Storage Schema
  - SS04 Relationship §5.1 PostgreSQL Schema
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "002_add_emotion_rel"
down_revision = "001_add_memory_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # SS03: emotion_states (current state per user × character)
    # ============================================================
    op.execute(
        """
    CREATE TABLE emotion_states (
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,

        -- VAD
        vad_valence FLOAT NOT NULL DEFAULT 0 CHECK (vad_valence BETWEEN -1 AND 1),
        vad_arousal FLOAT NOT NULL DEFAULT 0.3 CHECK (vad_arousal BETWEEN 0 AND 1),
        vad_dominance FLOAT NOT NULL DEFAULT 0.5 CHECK (vad_dominance BETWEEN 0 AND 1),

        vad_target_valence FLOAT NOT NULL DEFAULT 0,
        vad_target_arousal FLOAT NOT NULL DEFAULT 0.3,
        vad_target_dominance FLOAT NOT NULL DEFAULT 0.5,

        -- Active Emotion Stack (JSON array of ActiveEmotion)
        active_stack JSONB NOT NULL DEFAULT '[]'::jsonb,

        -- Mood
        mood JSONB NOT NULL,

        -- Energy
        energy FLOAT NOT NULL DEFAULT 0.6 CHECK (energy BETWEEN 0 AND 1),
        energy_baseline FLOAT NOT NULL DEFAULT 0.6,

        -- Trajectory & Triggers
        recent_vad_history JSONB NOT NULL DEFAULT '[]'::jsonb,
        recent_triggers JSONB NOT NULL DEFAULT '[]'::jsonb,

        -- Pending Repairs
        pending_repairs JSONB NOT NULL DEFAULT '[]'::jsonb,

        -- Meta
        loaded_from_previous BOOLEAN NOT NULL DEFAULT false,
        session_id UUID,
        last_turn_processed_at TIMESTAMP,
        last_mood_drift_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

        -- Optimistic lock
        version BIGINT NOT NULL DEFAULT 1,

        PRIMARY KEY (user_id, character_id)
    ) PARTITION BY HASH (user_id)
    """
    )

    # Create 16 partitions for emotion_states
    for i in range(16):
        op.execute(
            f"""
        CREATE TABLE emotion_states_p{i} PARTITION OF emotion_states
            FOR VALUES WITH (modulus 16, remainder {i})
        """
        )

    # Indexes on emotion_states
    op.execute(
        """
    CREATE INDEX idx_emotion_pending_repair ON emotion_states ((jsonb_array_length(pending_repairs)))
        WHERE jsonb_array_length(pending_repairs) > 0
    """
    )
    op.execute(
        """
    CREATE INDEX idx_emotion_mood_drift ON emotion_states (last_mood_drift_at)
    """
    )

    # ============================================================
    # SS03: emotion_events (append-only audit log)
    # ============================================================
    op.execute(
        """
    CREATE TABLE emotion_events (
        event_id UUID DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,

        event_type VARCHAR(50) NOT NULL,

        payload JSONB NOT NULL,

        turn_index BIGINT,
        source_turn_id UUID,

        -- VAD snapshot for diagnosability
        vad_before JSONB,
        vad_after JSONB,

        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    ) PARTITION BY RANGE (created_at)
    """
    )

    # Create initial partition for current month (May 2026)
    op.execute(
        """
    CREATE TABLE emotion_events_2026_05 PARTITION OF emotion_events
        FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """
    )

    # Add PK (must include partition key for partitioned tables)
    op.execute("ALTER TABLE emotion_events ADD PRIMARY KEY (event_id, created_at)")

    # Indexes on emotion_events
    op.execute(
        """
    CREATE INDEX idx_eevents_user_time ON emotion_events (user_id, character_id, created_at DESC)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_eevents_type ON emotion_events (event_type, created_at DESC)
    """
    )

    # ============================================================
    # SS04: relationship_states (current state per user × character)
    # ============================================================
    op.execute(
        """
    CREATE TABLE relationship_states (
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,

        -- Stage
        current_stage VARCHAR(30) NOT NULL DEFAULT 'STRANGER',
        previous_stage VARCHAR(30) NOT NULL DEFAULT 'STRANGER',
        stage_entered_at TIMESTAMP NOT NULL DEFAULT NOW(),
        highest_stage_reached VARCHAR(30) NOT NULL DEFAULT 'STRANGER',

        -- Continuous Dimensions
        intimacy_level FLOAT NOT NULL DEFAULT 0 CHECK (intimacy_level BETWEEN 0 AND 1),
        trust_score FLOAT NOT NULL DEFAULT 0 CHECK (trust_score BETWEEN 0 AND 1),
        attachment_strength FLOAT NOT NULL DEFAULT 0 CHECK (attachment_strength BETWEEN 0 AND 1),
        conflict_debt FLOAT NOT NULL DEFAULT 0 CHECK (conflict_debt BETWEEN 0 AND 1),
        vulnerability_score FLOAT NOT NULL DEFAULT 0 CHECK (vulnerability_score BETWEEN 0 AND 1),

        -- History Counters
        total_interactions BIGINT NOT NULL DEFAULT 0,
        total_meaningful_disclosures INT NOT NULL DEFAULT 0,
        total_promises_made INT NOT NULL DEFAULT 0,
        total_promises_kept INT NOT NULL DEFAULT 0,
        total_conflicts INT NOT NULL DEFAULT 0,
        total_repairs INT NOT NULL DEFAULT 0,
        total_successful_repairs INT NOT NULL DEFAULT 0,

        -- Time Markers
        first_meeting_at TIMESTAMP NOT NULL DEFAULT NOW(),
        last_interaction_at TIMESTAMP,
        longest_absence_days INT NOT NULL DEFAULT 0,
        longest_continuous_streak_days INT NOT NULL DEFAULT 0,

        -- Soul Modulation
        soul_modifiers JSONB NOT NULL,

        -- Special States
        active_special_states JSONB NOT NULL DEFAULT '[]'::jsonb,

        -- Stage Metadata
        stage_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

        -- Rituals
        rituals JSONB NOT NULL DEFAULT '{}'::jsonb,

        -- Recent Events (denormalized, limited size)
        recent_progression_events JSONB NOT NULL DEFAULT '[]'::jsonb,
        recent_regression_events JSONB NOT NULL DEFAULT '[]'::jsonb,
        recent_conflicts JSONB NOT NULL DEFAULT '[]'::jsonb,
        recent_repairs JSONB NOT NULL DEFAULT '[]'::jsonb,

        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

        -- Optimistic lock
        version BIGINT NOT NULL DEFAULT 1,

        PRIMARY KEY (user_id, character_id)
    ) PARTITION BY HASH (user_id)
    """
    )

    # Create 16 partitions for relationship_states
    for i in range(16):
        op.execute(
            f"""
        CREATE TABLE relationship_states_p{i} PARTITION OF relationship_states
            FOR VALUES WITH (modulus 16, remainder {i})
        """
        )

    # Indexes on relationship_states
    op.execute(
        """
    CREATE INDEX idx_rel_stage ON relationship_states (current_stage)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_rel_drifting ON relationship_states (last_interaction_at)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_rel_cold_war ON relationship_states ((jsonb_array_length(active_special_states)))
        WHERE jsonb_array_length(active_special_states) > 0
    """
    )

    # ============================================================
    # SS04: relationship_events (append-only audit log)
    # ============================================================
    op.execute(
        """
    CREATE TABLE relationship_events (
        event_id UUID DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        character_id VARCHAR(50) NOT NULL,

        event_type VARCHAR(50) NOT NULL,

        payload JSONB NOT NULL,

        -- State snapshots
        state_before JSONB,
        state_after JSONB,

        triggered_by_turn_id UUID,

        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    ) PARTITION BY RANGE (created_at)
    """
    )

    # Create initial partition for current month (May 2026)
    op.execute(
        """
    CREATE TABLE relationship_events_2026_05 PARTITION OF relationship_events
        FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """
    )

    # Add PK (must include partition key for partitioned tables)
    op.execute("ALTER TABLE relationship_events ADD PRIMARY KEY (event_id, created_at)")

    # Indexes on relationship_events
    op.execute(
        """
    CREATE INDEX idx_relevent_user ON relationship_events (user_id, character_id, created_at DESC)
    """
    )
    op.execute(
        """
    CREATE INDEX idx_relevent_type ON relationship_events (event_type, created_at DESC)
    """
    )


def downgrade() -> None:
    # Drop in reverse dependency order (events before states, leaf tables first)
    # CASCADE ensures partitioned child tables are dropped
    op.execute("DROP TABLE IF EXISTS relationship_events CASCADE")
    op.execute("DROP TABLE IF EXISTS relationship_states CASCADE")
    op.execute("DROP TABLE IF EXISTS emotion_events CASCADE")
    op.execute("DROP TABLE IF EXISTS emotion_states CASCADE")
