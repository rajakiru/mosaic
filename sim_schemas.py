"""Pydantic models for the simulation pipeline.

Copied from ~/akinator/models/schemas.py — standalone, no DB dependency.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class DecisionTemplate(BaseModel):
    """LLM-generated template that tailors the entire pipeline to the decision type."""
    decision_type: str = Field(description="Category: startup_quit, career_change, education, relocation, investment, etc.")
    factors: list[str] = Field(description="4 simulation factor names, e.g. ['financial', 'opportunity', 'alternative', 'wellbeing']")
    intake_questions: list[str] = Field(description="Exactly 5 intake questions tailored to this decision")
    graph_root_label: str = Field(description="Short label for the DAG root node, e.g. 'Leave MS?'")
    factor_labels: dict[str, str] = Field(description="Map factor id -> human-readable label, e.g. {'financial': 'Financial Survival'}")


class IntakeProfile(BaseModel):
    """Generic intake profile — answers keyed by q1..q5."""
    decision_type: str = Field(description="Decision type from classification")
    factors: list[str] = Field(description="Factor names from template")
    q1: str = Field(description="Answer to question 1")
    q2: str = Field(description="Answer to question 2")
    q3: str = Field(description="Answer to question 3")
    q4: str = Field(description="Answer to question 4")
    q5: str = Field(description="Answer to question 5")
    raw_description: str = Field(default="", description="Original user decision description")


class ResearchBrief(BaseModel):
    """Generic research brief with decision-type-aware fields."""
    baseline_estimates: list[dict] = Field(default_factory=list, description="Key numeric estimates as [{name, value}] pairs")
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors")
    opportunity_factors: list[str] = Field(default_factory=list, description="Identified upside factors")
    notes: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class FinancialModel(BaseModel):
    current_savings: float = Field(description="Starting cash balance")
    monthly_burn: float = Field(description="Monthly expenses")
    burn_volatility: float = Field(default=0.1, ge=0.0, le=1.0, description="Monthly burn variance as fraction")
    emergency_threshold: float = Field(default=2000, description="Cash level triggering stress")


class OpportunityModel(BaseModel):
    initial_progress: float = Field(default=0, description="Starting opportunity progress (e.g. initial MRR, initial traction)")
    growth_rate_mu: float = Field(default=0.05, description="Mean monthly growth rate")
    growth_rate_sigma: float = Field(default=0.08, ge=0.01, le=1.0, description="Growth rate volatility")
    setback_prob_monthly: float = Field(default=0.03, ge=0.0, le=0.5, description="Monthly probability of setback")
    setback_impact: float = Field(default=0.5, ge=0.0, le=1.0, description="Progress multiplier on setback")
    success_threshold: float = Field(default=10000, description="Progress level considered success")


class AlternativeModel(BaseModel):
    alternative_monthly_value: float = Field(default=10000, description="Monthly value of the forgone alternative (salary, etc.)")
    reentry_time_months_mu: float = Field(default=3.0, ge=0.5, le=24.0, description="Mean months to re-enter alternative path")
    reentry_time_months_sigma: float = Field(default=1.5, ge=0.1, le=12.0)
    value_impact_pct: float = Field(default=-0.05, ge=-0.5, le=0.5, description="Value change on re-entry (e.g. salary penalty)")


class WellbeingModel(BaseModel):
    base_stress: float = Field(default=0.3, ge=0.0, le=1.0, description="Baseline stress level")
    cash_stress_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    progress_stress_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    time_pressure_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    burnout_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Stress level triggering burnout")
    recovery_rate: float = Field(default=0.05, ge=0.0, le=0.5, description="Monthly stress recovery")


class SimConfig(BaseModel):
    n_sims: int = Field(default=1000, ge=100, le=10000)
    horizon_months: int = Field(default=18, ge=6, le=60)
    decision_type: str = Field(default="generic", description="Decision type from classification")
    factors: list[str] = Field(default_factory=lambda: ["financial", "opportunity", "alternative", "wellbeing"])
    financial_model: FinancialModel
    opportunity_model: OpportunityModel
    alternative_model: AlternativeModel = Field(default_factory=AlternativeModel)
    wellbeing_model: WellbeingModel = Field(default_factory=WellbeingModel)
    seed: Optional[int] = None


class NodeKPIs(BaseModel):
    financial: dict = Field(default_factory=dict)
    opportunity: dict = Field(default_factory=dict)
    alternative: dict = Field(default_factory=dict)
    wellbeing: dict = Field(default_factory=dict)


class SimResults(BaseModel):
    cash_traces: list[list[float]] = Field(description="Sample cash balance traces for charting")
    runway_histogram: list[float] = Field(description="Months until cash=0 for each sim")
    outcome_probabilities: dict[str, float] = Field(description="p_financial_failure, p_success, p_opportunity_failure, p_stagnation")
    sensitivity: dict = Field(default_factory=dict, description="Parameter -> {metric -> delta}")
    node_kpis: NodeKPIs = Field(default_factory=NodeKPIs)
    seed: Optional[int] = None
