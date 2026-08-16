"""Initial schema — create all six tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # coverage_rates
    # ------------------------------------------------------------------
    op.create_table(
        "coverage_rates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("state_abbr", sa.String(2), nullable=True),
        sa.Column("state_fips", sa.String(2), nullable=True),
        sa.Column("vaccine_code", sa.String(20), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("demographic_category", sa.String(50), nullable=True),
        sa.Column("demographic_value", sa.String(100), nullable=True),
        sa.Column("coverage_rate", sa.Numeric(5, 1), nullable=True),
        sa.Column("ci_lower", sa.Numeric(5, 1), nullable=True),
        sa.Column("ci_upper", sa.Numeric(5, 1), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column(
            "loaded_at",
            sa.DateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coverage_rates_state_vaccine_year",
        "coverage_rates",
        ["state_abbr", "vaccine_code", "year"],
    )
    op.create_index(
        "ix_coverage_rates_vaccine_year",
        "coverage_rates",
        ["vaccine_code", "year"],
    )

    # ------------------------------------------------------------------
    # vaers_reports
    # ------------------------------------------------------------------
    op.create_table(
        "vaers_reports",
        sa.Column("vaers_id", sa.Integer(), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("state_abbr", sa.String(2), nullable=True),
        sa.Column("age_years", sa.Numeric(5, 1), nullable=True),
        sa.Column("sex", sa.String(1), nullable=True),
        sa.Column("died", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("life_threatening", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("hospitalized", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("hospital_days", sa.Integer(), nullable=True),
        sa.Column("disabled", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("recovered", sa.Boolean(), nullable=True),
        sa.Column("vax_date", sa.Date(), nullable=True),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("onset_days", sa.Integer(), nullable=True),
        sa.Column("serious", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("data_year", sa.Integer(), nullable=True),
        sa.Column(
            "loaded_at",
            sa.DateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("vaers_id"),
    )
    op.create_index("ix_vaers_reports_data_year", "vaers_reports", ["data_year"])
    op.create_index("ix_vaers_reports_state_abbr", "vaers_reports", ["state_abbr"])

    # ------------------------------------------------------------------
    # vaers_vaccines
    # ------------------------------------------------------------------
    op.create_table(
        "vaers_vaccines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vaers_id", sa.Integer(), nullable=False),
        sa.Column("vax_type", sa.String(50), nullable=True),
        sa.Column("vax_manufacturer", sa.String(100), nullable=True),
        sa.Column("vax_dose_series", sa.String(20), nullable=True),
        sa.Column("vax_route", sa.String(20), nullable=True),
        sa.Column("vax_site", sa.String(30), nullable=True),
        sa.ForeignKeyConstraint(["vaers_id"], ["vaers_reports.vaers_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vaers_vaccines_vaers_id", "vaers_vaccines", ["vaers_id"])
    op.create_index("ix_vaers_vaccines_vax_type", "vaers_vaccines", ["vax_type"])

    # ------------------------------------------------------------------
    # vaers_symptoms
    # ------------------------------------------------------------------
    op.create_table(
        "vaers_symptoms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vaers_id", sa.Integer(), nullable=False),
        sa.Column("symptom", sa.String(200), nullable=True),
        sa.Column("meddra_version", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(["vaers_id"], ["vaers_reports.vaers_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vaers_symptoms_vaers_id", "vaers_symptoms", ["vaers_id"])
    op.create_index("ix_vaers_symptoms_symptom", "vaers_symptoms", ["symptom"])

    # ------------------------------------------------------------------
    # ae_summary
    # ------------------------------------------------------------------
    op.create_table(
        "ae_summary",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data_year", sa.Integer(), nullable=True),
        sa.Column("vax_type", sa.String(50), nullable=True),
        sa.Column("symptom", sa.String(200), nullable=True),
        sa.Column("report_count", sa.Integer(), nullable=True),
        sa.Column("serious_count", sa.Integer(), nullable=True),
        sa.Column("prr", sa.Numeric(8, 4), nullable=True),
        sa.Column("chi_squared", sa.Numeric(8, 4), nullable=True),
        sa.Column(
            "calculated_at",
            sa.DateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ae_summary_vax_type_data_year",
        "ae_summary",
        ["vax_type", "data_year"],
    )

    # ------------------------------------------------------------------
    # adherence_rates
    # ------------------------------------------------------------------
    op.create_table(
        "adherence_rates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vaccine_series", sa.String(50), nullable=True),
        sa.Column("dose_number", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("state_abbr", sa.String(2), nullable=True),
        sa.Column("demographic_category", sa.String(50), nullable=True),
        sa.Column("demographic_value", sa.String(100), nullable=True),
        sa.Column("completion_rate", sa.Numeric(5, 1), nullable=True),
        sa.Column("on_time_rate", sa.Numeric(5, 1), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column(
            "loaded_at",
            sa.DateTime(),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_adherence_rates_series_year_state",
        "adherence_rates",
        ["vaccine_series", "year", "state_abbr"],
    )


def downgrade() -> None:
    op.drop_table("adherence_rates")
    op.drop_table("ae_summary")
    op.drop_table("vaers_symptoms")
    op.drop_table("vaers_vaccines")
    op.drop_table("vaers_reports")
    op.drop_table("coverage_rates")
