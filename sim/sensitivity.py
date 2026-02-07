"""One-at-a-time (OAT) sensitivity analysis.

Varies each key parameter by +20% and -20%, reruns a smaller batch, and measures
the KPI deltas for multiple metrics.
"""
from __future__ import annotations
from sim_schemas import SimConfig
from sim.engine import run_monte_carlo

SENSITIVITY_SIMS = 200
VARIATION = 0.20  # +/- 20%

# Parameters to vary: (display_name, model_attr, field_name)
PARAMS_TO_VARY = [
    ("monthly_burn", "financial_model", "monthly_burn"),
    ("burn_volatility", "financial_model", "burn_volatility"),
    ("growth_rate_mu", "opportunity_model", "growth_rate_mu"),
    ("growth_rate_sigma", "opportunity_model", "growth_rate_sigma"),
    ("setback_prob", "opportunity_model", "setback_prob_monthly"),
    ("base_stress", "wellbeing_model", "base_stress"),
    ("alternative_value", "alternative_model", "alternative_monthly_value"),
]

TARGET_METRICS = ["p_financial_failure", "p_success"]


def _clamp_to_field_bounds(sub_model, field_name: str, value: float) -> float:
    """Clamp value to Pydantic field bounds if they exist."""
    field_info = sub_model.model_fields.get(field_name)
    if field_info and field_info.metadata:
        for m in field_info.metadata:
            if hasattr(m, "le"):
                value = min(value, m.le)
            if hasattr(m, "ge"):
                value = max(value, m.ge)
    return value


def run_sensitivity(base_config: SimConfig) -> dict:
    """Return {param_direction: {metric: delta}} for each parameter varied +/- 20%.

    Example: {"monthly_burn_up": {"p_financial_failure": 0.05, "p_success": -0.02}, ...}
    """
    baseline_cfg = base_config.model_copy(deep=True)
    baseline_cfg.n_sims = SENSITIVITY_SIMS
    baseline = run_monte_carlo(baseline_cfg)
    baseline_probs = baseline.outcome_probabilities

    results = {}

    for name, model_attr, field_name in PARAMS_TO_VARY:
        for direction, factor in [("up", 1 + VARIATION), ("down", 1 - VARIATION)]:
            cfg = base_config.model_copy(deep=True)
            cfg.n_sims = SENSITIVITY_SIMS

            sub_model = getattr(cfg, model_attr)
            base_val = getattr(sub_model, field_name)

            new_val = base_val * factor
            new_val = _clamp_to_field_bounds(sub_model, field_name, new_val)
            setattr(sub_model, field_name, new_val)

            result = run_monte_carlo(cfg)

            deltas = {}
            for metric in TARGET_METRICS:
                delta = result.outcome_probabilities.get(metric, 0) - baseline_probs.get(metric, 0)
                deltas[metric] = round(delta, 4)

            results[f"{name}_{direction}"] = deltas

    return results
