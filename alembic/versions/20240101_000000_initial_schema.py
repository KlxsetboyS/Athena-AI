"""Initial schema – Sprints 1.1–1.5 (Competition → OddsSelection)

Revision ID: 001_initial_schema
Revises: None
Create Date: 2024-01-01 00:00:00.000000

Creates all Athena AI domain tables with full constraints, indexes, and FKs.
Tables (in dependency order):
  1. competition
  2. season
  3. team
  4. season_team
  5. match
  6. match_result
  7. bookmaker
  8. odds_snapshot
  9. odds_selection
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. competition ────────────────────────────────────────────────────────
    op.create_table(
        "competition",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("country_code", sa.String(3), nullable=True),
        sa.Column(
            "competition_type",
            sa.Enum(
                "league", "cup", "international", "playoff", "friendly",
                name="competitiontype",
            ),
            nullable=False,
        ),
        sa.Column(
            "gender",
            sa.Enum("male", "female", "mixed", name="competitiongender"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(64), nullable=True),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_competition"),
        sa.UniqueConstraint("external_id", name="uq_competition_external_id"),
        sa.CheckConstraint("length(name) >= 2", name="ck_competition_name_min_length"),
    )
    op.create_index("ix_competition_id", "competition", ["id"])

    # ── 2. season ─────────────────────────────────────────────────────────────
    op.create_table(
        "season",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("competition_id", sa.Uuid(), nullable=False),
        sa.Column("year_start", sa.Integer(), nullable=False),
        sa.Column("year_end", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(20), nullable=True),
        sa.Column(
            "status",
            sa.Enum("upcoming", "active", "finished", "suspended", name="seasonstatus"),
            nullable=False,
        ),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_season"),
        sa.ForeignKeyConstraint(
            ["competition_id"], ["competition.id"],
            name="fk_season_competition_id_competition",
        ),
        sa.UniqueConstraint("competition_id", "year_start", name="uq_season_competition_year"),
        sa.CheckConstraint("year_end >= year_start", name="ck_season_year_order"),
    )
    op.create_index("ix_season_id", "season", ["id"])

    # ── 3. team ───────────────────────────────────────────────────────────────
    op.create_table(
        "team",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("short_name", sa.String(10), nullable=True),
        sa.Column("country_code", sa.String(3), nullable=True),
        sa.Column(
            "gender",
            sa.Enum("male", "female", "mixed", name="teamgender"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(64), nullable=True),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_team"),
        sa.UniqueConstraint("external_id", name="uq_team_external_id"),
        sa.CheckConstraint("length(name) >= 2", name="ck_team_name_min_length"),
    )
    op.create_index("ix_team_id", "team", ["id"])

    # ── 4. season_team ────────────────────────────────────────────────────────
    op.create_table(
        "season_team",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_season_team"),
        sa.ForeignKeyConstraint(
            ["season_id"], ["season.id"],
            name="fk_season_team_season_id_season",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"], ["team.id"],
            name="fk_season_team_team_id_team",
        ),
        sa.UniqueConstraint("season_id", "team_id", name="uq_season_team"),
    )
    op.create_index("ix_season_team_id", "season_team", ["id"])

    # ── 5. match ──────────────────────────────────────────────────────────────
    op.create_table(
        "match",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("competition_id", sa.Uuid(), nullable=False),
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("home_team_id", sa.Uuid(), nullable=False),
        sa.Column("away_team_id", sa.Uuid(), nullable=False),
        sa.Column("kickoff_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue", sa.String(120), nullable=True),
        sa.Column("matchday", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "scheduled", "postponed", "cancelled", "live",
                "half_time", "finished", "abandoned", "awarded",
                name="matchstatus",
            ),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(64), nullable=True),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_match"),
        sa.ForeignKeyConstraint(
            ["competition_id"], ["competition.id"],
            name="fk_match_competition_id_competition",
        ),
        sa.ForeignKeyConstraint(
            ["season_id"], ["season.id"],
            name="fk_match_season_id_season",
        ),
        sa.ForeignKeyConstraint(
            ["home_team_id"], ["team.id"],
            name="fk_match_home_team_id_team",
        ),
        sa.ForeignKeyConstraint(
            ["away_team_id"], ["team.id"],
            name="fk_match_away_team_id_team",
        ),
        sa.UniqueConstraint(
            "season_id", "home_team_id", "away_team_id", "kickoff_time_utc",
            name="uq_match_unique",
        ),
        sa.UniqueConstraint("external_id", name="uq_match_external_id"),
        sa.CheckConstraint("home_team_id != away_team_id", name="ck_match_teams_must_differ"),
        sa.CheckConstraint("matchday >= 1", name="ck_match_matchday_positive"),
    )
    op.create_index("ix_match_id", "match", ["id"])
    op.create_index("ix_match_kickoff_time_utc", "match", ["kickoff_time_utc"])
    op.create_index("ix_match_status", "match", ["status"])
    op.create_index("ix_match_season_id", "match", ["season_id"])

    # ── 6. match_result ───────────────────────────────────────────────────────
    op.create_table(
        "match_result",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column(
            "result_type",
            sa.Enum("home_win", "draw", "away_win", name="resulttype"),
            nullable=True,
        ),
        sa.Column(
            "match_status",
            sa.Enum(
                "finished", "cancelled", "postponed", "abandoned", "awarded",
                name="matchresultstatus",
            ),
            nullable=False,
        ),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_match_result"),
        sa.ForeignKeyConstraint(
            ["match_id"], ["match.id"],
            name="fk_match_result_match_id_match",
        ),
        sa.UniqueConstraint("match_id", name="uq_match_result_match"),
        sa.CheckConstraint("home_score >= 0", name="ck_match_result_home_score_non_negative"),
        sa.CheckConstraint("away_score >= 0", name="ck_match_result_away_score_non_negative"),
        sa.CheckConstraint(
            "(home_score IS NULL) = (away_score IS NULL)",
            name="ck_match_result_scores_both_or_neither",
        ),
        sa.CheckConstraint(
            "result_type IS NULL OR match_status = 'finished'",
            name="ck_match_result_type_only_when_finished",
        ),
    )
    op.create_index("ix_match_result_id", "match_result", ["id"])
    op.create_index("ix_match_result_match_id", "match_result", ["match_id"])

    # ── 7. bookmaker ─────────────────────────────────────────────────────────
    op.create_table(
        "bookmaker",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("country_code", sa.String(3), nullable=True),
        sa.Column("is_exchange", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("external_id", sa.String(64), nullable=True),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_bookmaker"),
        sa.UniqueConstraint("slug", name="uq_bookmaker_slug"),
        sa.UniqueConstraint("external_id", name="uq_bookmaker_external_id"),
        sa.CheckConstraint("length(name) >= 2", name="ck_bookmaker_name_min_length"),
        sa.CheckConstraint("length(slug) >= 2", name="ck_bookmaker_slug_min_length"),
    )
    op.create_index("ix_bookmaker_id", "bookmaker", ["id"])
    op.create_index("ix_bookmaker_slug", "bookmaker", ["slug"])

    # ── 8. odds_snapshot ─────────────────────────────────────────────────────
    op.create_table(
        "odds_snapshot",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("bookmaker_id", sa.Uuid(), nullable=False),
        sa.Column(
            "market",
            sa.Enum(
                "match_winner", "over_under", "btts", "asian_handicap", "double_chance",
                name="oddsmarket",
            ),
            nullable=False,
        ),
        sa.Column(
            "odds_format",
            sa.Enum("decimal", "fractional", "american", name="oddsformat"),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_closing", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("external_ref", sa.String(128), nullable=True),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_odds_snapshot"),
        sa.ForeignKeyConstraint(
            ["match_id"], ["match.id"],
            name="fk_odds_snapshot_match_id_match",
        ),
        sa.ForeignKeyConstraint(
            ["bookmaker_id"], ["bookmaker.id"],
            name="fk_odds_snapshot_bookmaker_id_bookmaker",
        ),
        sa.UniqueConstraint("external_ref", name="uq_odds_snapshot_external_ref"),
        sa.CheckConstraint("length(source) >= 1", name="ck_odds_snapshot_source_not_empty"),
    )
    op.create_index("ix_odds_snapshot_id", "odds_snapshot", ["id"])
    # Composite index for match/bookmaker/time queries
    op.create_index(
        "ix_odds_snapshot_match_bookmaker_captured",
        "odds_snapshot",
        ["match_id", "bookmaker_id", "captured_at"],
    )
    # Index for closing-line queries
    op.create_index(
        "ix_odds_snapshot_is_closing",
        "odds_snapshot",
        ["match_id", "is_closing"],
    )

    # ── 9. odds_selection ────────────────────────────────────────────────────
    op.create_table(
        "odds_selection",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column(
            "selection_type",
            sa.Enum(
                "home", "draw", "away", "over", "under", "yes", "no",
                name="selectiontype",
            ),
            nullable=False,
        ),
        sa.Column("label", sa.String(60), nullable=True),
        sa.Column("decimal_odd", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("line", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        # BaseModel columns
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_odds_selection"),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], ["odds_snapshot.id"],
            name="fk_odds_selection_snapshot_id_odds_snapshot",
        ),
        sa.UniqueConstraint(
            "snapshot_id", "selection_type", "line",
            name="uq_odds_selection_snapshot_type_line",
        ),
        sa.CheckConstraint("decimal_odd >= 1.01", name="ck_odds_selection_decimal_odd_minimum"),
        sa.CheckConstraint("line IS NULL OR line > 0", name="ck_odds_selection_line_positive_when_set"),
    )
    op.create_index("ix_odds_selection_id", "odds_selection", ["id"])
    op.create_index("ix_odds_selection_snapshot_id", "odds_selection", ["snapshot_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("odds_selection")
    op.drop_table("odds_snapshot")
    op.drop_table("bookmaker")
    op.drop_table("match_result")
    op.drop_table("match")
    op.drop_table("season_team")
    op.drop_table("team")
    op.drop_table("season")
    op.drop_table("competition")

    # Drop enum types (PostgreSQL only — SQLite ignores these)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum_name in [
            "competitiontype", "competitiongender",
            "seasonstatus",
            "teamgender",
            "matchstatus",
            "resulttype", "matchresultstatus",
            "oddsmarket", "oddsformat", "selectiontype",
        ]:
            op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
