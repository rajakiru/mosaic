"""Generic Monte Carlo simulation runner."""
from __future__ import annotations
import numpy as np
import time
from sim_schemas import SimConfig, SimResults, NodeKPIs
from sim.models import SimState, SimTrace
from sim.domains.generic import STEP_REGISTRY


MAX_RUNTIME_SECONDS = 5.0
MAX_SAMPLE_TRACES = 50


def _classify_outcome(state: SimState, config: SimConfig) -> str:
    """Classify a single simulation into mutually exclusive outcome buckets."""
    if state.ran_out:
        return "financial_failure"
    if state.opportunity_succeeded:
        return "success"
    if state.opportunity_failed or state.opportunity_progress < config.opportunity_model.initial_progress:
        return "opportunity_failure"
    return "stagnation"


def run_monte_carlo(config: SimConfig, progress_callback=None) -> SimResults:
    """Run N simulations and return aggregated results."""
    seed = config.seed or int(time.time() * 1000) % (2**31)
    rng = np.random.default_rng(seed)
    n = config.n_sims
    horizon = config.horizon_months

    # Resolve step functions from config.factors
    steps = []
    for factor in config.factors:
        fn = STEP_REGISTRY.get(factor)
        if fn:
            steps.append(fn)

    all_traces: list[SimTrace] = []
    all_final_states: list[SimState] = []
    start_time = time.time()

    for i in range(n):
        if time.time() - start_time > MAX_RUNTIME_SECONDS:
            n = i
            break

        state = SimState(
            cash_balance=config.financial_model.current_savings,
            opportunity_progress=config.opportunity_model.initial_progress,
        )
        trace = SimTrace()

        for month in range(horizon):
            state.month = month

            for step_fn in steps:
                step_fn(state, config, rng)

            trace.cash.append(state.cash_balance)
            trace.opportunity.append(state.opportunity_progress)
            trace.stress.append(state.stress_index)

            if state.ran_out and trace.runway_month is None:
                trace.runway_month = month

        # Classify outcome
        trace.outcome = _classify_outcome(state, config)
        all_traces.append(trace)
        all_final_states.append(state)

        if progress_callback and (i % 100 == 0 or i == n - 1):
            progress_callback(i + 1, n)

    # Build results
    n_total = max(len(all_traces), 1)

    # Sample traces for charting
    sample_indices = rng.choice(len(all_traces), size=min(MAX_SAMPLE_TRACES, len(all_traces)), replace=False)
    cash_traces = [all_traces[i].cash for i in sample_indices]

    # Runway histogram
    runway_hist = [
        t.runway_month if t.runway_month is not None else horizon + 1
        for t in all_traces
    ]

    # Outcome probabilities — mutually exclusive, sum to 1.0
    outcome_counts = {"financial_failure": 0, "success": 0, "opportunity_failure": 0, "stagnation": 0}
    for t in all_traces:
        if t.outcome in outcome_counts:
            outcome_counts[t.outcome] += 1

    outcome_probs = {
        f"p_{k}": round(v / n_total, 3)
        for k, v in outcome_counts.items()
    }

    # Node KPIs
    final_cash = [t.cash[-1] for t in all_traces if t.cash]
    final_stress = [t.stress[-1] for t in all_traces if t.stress]
    final_opportunity = [t.opportunity[-1] for t in all_traces if t.opportunity]
    runway_months_list = [
        t.runway_month if t.runway_month is not None else horizon
        for t in all_traces
    ]

    node_kpis = NodeKPIs(
        financial={
            "p_financial_failure": outcome_probs.get("p_financial_failure", 0),
            "median_runway": round(float(np.median(runway_months_list)), 1),
            "median_final_cash": round(float(np.median(final_cash)), 0) if final_cash else 0,
        },
        opportunity={
            "p_success": outcome_probs.get("p_success", 0),
            "p_opportunity_failure": outcome_probs.get("p_opportunity_failure", 0),
            "median_final_progress": round(float(np.median(final_opportunity)), 0) if final_opportunity else 0,
        },
        alternative={
            "total_forgone_value": round(
                float(np.mean([s.alternative_cost for s in all_final_states])), 0
            ),
            "worst_case_cash_p10": round(float(np.percentile(final_cash, 10)), 0) if final_cash else 0,
        },
        wellbeing={
            "p_burnout": round(
                sum(1 for t in all_traces if t.stress and t.stress[-1] > config.wellbeing_model.burnout_threshold)
                / n_total, 3
            ),
            "median_stress": round(float(np.median(final_stress)), 3) if final_stress else 0,
        },
    )

    return SimResults(
        cash_traces=cash_traces,
        runway_histogram=runway_hist,
        outcome_probabilities=outcome_probs,
        sensitivity={},
        node_kpis=node_kpis,
        seed=seed,
    )
