"""Generic domain step functions for the 4 simulation nodes.

Each function mutates the SimState in place for one month step.
"""
from __future__ import annotations
import numpy as np
from sim.models import SimState
from sim_schemas import SimConfig


def financial_step(state: SimState, config: SimConfig, rng: np.random.Generator):
    """Node 1: Financial Survival — update cash balance."""
    fin = config.financial_model
    # Monthly burn with volatility
    burn_shock = rng.normal(1.0, fin.burn_volatility)
    actual_burn = fin.monthly_burn * max(burn_shock, 0.5)

    # Revenue from opportunity progress (if any)
    revenue = state.opportunity_progress

    state.cash_balance += revenue - actual_burn

    if state.cash_balance <= 0 and not state.ran_out:
        state.ran_out = True


def opportunity_step(state: SimState, config: SimConfig, rng: np.random.Generator):
    """Node 2: Opportunity Progress — traction and growth toward success."""
    opp = config.opportunity_model

    if state.opportunity_failed:
        return

    # Check for setback
    if rng.random() < opp.setback_prob_monthly:
        state.opportunity_progress *= opp.setback_impact
        state.setback_count += 1
        # After 3 setbacks, opportunity fails
        if state.setback_count >= 3:
            state.opportunity_failed = True
            state.opportunity_progress = 0
            return

    # Growth
    growth = rng.normal(opp.growth_rate_mu, opp.growth_rate_sigma)
    if state.opportunity_progress < 1:
        # Pre-traction: chance of initial progress
        months_in = state.month + 1
        p_first = min(0.15, 0.02 * months_in)
        if rng.random() < p_first:
            state.opportunity_progress = rng.uniform(100, 2000)
    else:
        state.opportunity_progress = max(0, state.opportunity_progress * (1 + growth))

    if state.opportunity_progress >= opp.success_threshold:
        state.opportunity_succeeded = True


def alternative_step(state: SimState, config: SimConfig, rng: np.random.Generator):
    """Node 3: Alternative/Opportunity Cost — track forgone value."""
    alt = config.alternative_model
    state.alternative_cost += alt.alternative_monthly_value


def wellbeing_step(state: SimState, config: SimConfig, rng: np.random.Generator):
    """Node 4: Wellbeing/Stress Risk — accumulate stress."""
    wb = config.wellbeing_model
    fin = config.financial_model

    if state.burned_out:
        return

    # Cash stress: higher when cash is low relative to burn
    months_runway = state.cash_balance / max(fin.monthly_burn, 1)
    cash_stress = max(0, 1.0 - months_runway / 6.0)

    # Progress stress: higher when no progress
    opp = config.opportunity_model
    progress_stress = max(0, 1.0 - state.opportunity_progress / max(opp.success_threshold * 0.1, 1))

    # Time pressure: increases over horizon
    time_stress = state.month / config.horizon_months

    # Weighted stress index
    raw_stress = (
        wb.cash_stress_weight * cash_stress +
        wb.progress_stress_weight * progress_stress +
        wb.time_pressure_weight * time_stress
    )

    # Smooth toward raw stress with some noise
    noise = rng.normal(0, 0.05)
    state.stress_index = 0.7 * state.stress_index + 0.3 * raw_stress + noise
    state.stress_index = max(0.0, min(1.0, state.stress_index))

    # Natural recovery
    state.stress_index = max(0, state.stress_index - wb.recovery_rate)

    if state.stress_index >= wb.burnout_threshold:
        if rng.random() < 0.3:
            state.burned_out = True


# Registry mapping factor names to step functions
STEP_REGISTRY = {
    "financial": financial_step,
    "opportunity": opportunity_step,
    "alternative": alternative_step,
    "wellbeing": wellbeing_step,
}
