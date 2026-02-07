"""LLM utility functions for the simulation pipeline.

Adapted from ~/akinator/services/llm.py to use the Dedalus API
(OpenAI-compatible) via the openai Python library.
All functions accept a client and model parameter — no hardcoded model.
"""
from __future__ import annotations
import json
import logging
from openai import OpenAI
from sim_schemas import DecisionTemplate, IntakeProfile, ResearchBrief, SimConfig

logger = logging.getLogger(__name__)


def _parse_json(raw: str) -> dict:
    """Strip markdown code blocks and parse JSON from LLM response."""
    cleaned = raw.replace("```json\n", "").replace("```json", "")
    cleaned = cleaned.replace("```\n", "").replace("```", "").strip()
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM_PROMPT = """You are an AI decision-support agent. The user will describe a major life decision.

Your job is to classify their decision and produce a DecisionTemplate that will drive the entire analysis pipeline.

Rules:
1. decision_type: a short slug like "startup_quit", "career_change", "education", "relocation", "investment", etc.
2. factors: EXACTLY 4 factor IDs that will become simulation nodes. Always use these 4 generic names: ["financial", "opportunity", "alternative", "wellbeing"]. These map to:
   - financial: money/cash/savings tracking
   - opportunity: the primary path they're considering (startup growth, new career progress, education value, etc.)
   - alternative: the fallback/opportunity cost of what they're giving up
   - wellbeing: stress, satisfaction, burnout risk
3. intake_questions: EXACTLY 5 questions tailored to THIS specific decision. Each question should gather a concrete data point needed to parameterize a Monte Carlo simulation. Include response format hints in parentheses.
4. graph_root_label: short (2-4 words) label for the decision, e.g. "Leave MS?" or "Quit to Startup?"
5. factor_labels: human-readable names for each factor ID tailored to the decision context, e.g. {"financial": "Savings Runway", "opportunity": "Startup Growth", "alternative": "Career Cost", "wellbeing": "Burnout Risk"}

Return ONLY valid JSON matching this structure:
{"decision_type":"...","factors":["financial","opportunity","alternative","wellbeing"],"intake_questions":["Q1","Q2","Q3","Q4","Q5"],"graph_root_label":"...","factor_labels":{"financial":"...","opportunity":"...","alternative":"...","wellbeing":"..."}}"""


def classify_decision(client: OpenAI, model: str, decision_context: str) -> DecisionTemplate:
    """Classify the user's decision and generate a tailored template."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": decision_context},
        ],
        max_tokens=1000,
    )
    data = _parse_json(response.choices[0].message.content)
    return DecisionTemplate(**data)


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

def run_research(client: OpenAI, model: str, intake_profile: IntakeProfile, template: DecisionTemplate) -> ResearchBrief:
    """Run research to calibrate simulation priors (no web search — uses LLM knowledge)."""
    answers_text = "\n".join(
        f"- Q{i+1} ({template.intake_questions[i]}): {getattr(intake_profile, f'q{i+1}')}"
        for i in range(5)
    )

    research_prompt = f"""You are a research assistant helping calibrate a Monte Carlo simulation for a "{template.decision_type}" decision.

The user's answers:
{answers_text}

Produce a structured ResearchBrief with:
1. baseline_estimates: Key numeric estimates as [{{"name": "...", "value": number}}] pairs (costs, salaries, success rates, timelines, etc.)
2. risk_factors: Key risk factors (3-5 items)
3. opportunity_factors: Key upside factors (3-5 items)
4. notes: Any relevant observations (2-3 items)
5. sources: List relevant data sources you're drawing on

Return ONLY valid JSON:
{{"baseline_estimates":[{{"name":"...","value":0}}],"risk_factors":["..."],"opportunity_factors":["..."],"notes":["..."],"sources":["..."]}}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": research_prompt}],
            max_tokens=1200,
        )
        data = _parse_json(response.choices[0].message.content)
        return ResearchBrief(**data)
    except Exception as e:
        logger.warning(f"Research failed, using defaults: {e}")
        return _default_research_brief(intake_profile, template)


def _default_research_brief(profile: IntakeProfile, template: DecisionTemplate) -> ResearchBrief:
    """Fallback research brief with reasonable defaults."""
    return ResearchBrief(
        baseline_estimates=[
            {"name": "monthly_cost_estimate", "value": 3000},
            {"name": "success_rate_12m", "value": 0.35},
            {"name": "opportunity_value_monthly", "value": 8000},
        ],
        risk_factors=["Financial runway depletion", "Opportunity may not materialize", "High stress from uncertainty"],
        opportunity_factors=["Potential for significant upside", "Personal growth", "Long-term positioning"],
        notes=["Using default priors (research unavailable)"],
        sources=[],
    )


# ---------------------------------------------------------------------------
# Sim Config Generation
# ---------------------------------------------------------------------------

def generate_sim_config(
    client: OpenAI,
    model: str,
    intake_profile: IntakeProfile,
    research_brief: ResearchBrief,
    template: DecisionTemplate,
) -> SimConfig:
    """Have the LLM produce a SimConfig JSON based on intake + research."""
    answers_text = "\n".join(
        f"- Q{i+1} ({template.intake_questions[i]}): {getattr(intake_profile, f'q{i+1}')}"
        for i in range(5)
    )

    prompt = f"""You are calibrating a Monte Carlo simulation engine for a "{template.decision_type}" decision.

INTAKE ANSWERS:
{answers_text}

RESEARCH BRIEF:
- Baseline estimates: {json.dumps({e['name']: e['value'] for e in research_brief.baseline_estimates})}
- Risk factors: {', '.join(research_brief.risk_factors)}
- Opportunity factors: {', '.join(research_brief.opportunity_factors)}
- Notes: {'; '.join(research_brief.notes)}

The simulation uses 4 generic models:
1. financial_model: tracks cash balance (current_savings, monthly_burn, burn_volatility 0.05-0.2, emergency_threshold)
2. opportunity_model: tracks primary-path progress (initial_progress, growth_rate_mu, growth_rate_sigma, setback_prob_monthly 0-0.5, setback_impact 0-1, success_threshold)
3. alternative_model: tracks forgone alternative cost (alternative_monthly_value = monthly value of what's given up, reentry_time_months_mu/sigma, value_impact_pct)
4. wellbeing_model: tracks stress/burnout — ALL values MUST be 0.0-1.0 floats (base_stress, cash_stress_weight, progress_stress_weight, time_pressure_weight, burnout_threshold, recovery_rate). For example base_stress=0.3 means 30% stress.

Guidelines:
- decision_type = "{template.decision_type}"
- factors = {json.dumps(template.factors)}
- n_sims = 1000, horizon_months = 18 (or adjust if the decision warrants a longer/shorter horizon)
- Estimate current_savings from user answers. monthly_burn from user answers or research.
- For opportunity_model: initial_progress=0 if starting fresh. growth_rate_mu captures how fast progress builds. success_threshold is the level that means "it worked".
- For alternative_model: alternative_monthly_value = what they give up monthly (salary, stipend, etc.)
- Keep all parameters within the bounds specified in the model descriptions

Return ONLY valid JSON:
{{"n_sims":1000,"horizon_months":18,"decision_type":"...","factors":["financial","opportunity","alternative","wellbeing"],"financial_model":{{"current_savings":0,"monthly_burn":0,"burn_volatility":0.1,"emergency_threshold":2000}},"opportunity_model":{{"initial_progress":0,"growth_rate_mu":0.05,"growth_rate_sigma":0.08,"setback_prob_monthly":0.03,"setback_impact":0.5,"success_threshold":10000}},"alternative_model":{{"alternative_monthly_value":10000,"reentry_time_months_mu":3.0,"reentry_time_months_sigma":1.5,"value_impact_pct":-0.05}},"wellbeing_model":{{"base_stress":0.3,"cash_stress_weight":0.4,"progress_stress_weight":0.3,"time_pressure_weight":0.3,"burnout_threshold":0.8,"recovery_rate":0.05}}}}"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
    )

    data = _parse_json(response.choices[0].message.content)
    _clamp_sim_config(data)
    return SimConfig(**data)


def _clamp_sim_config(data: dict):
    """Enforce all Pydantic bounds on LLM-generated SimConfig values in-place."""
    # Top-level
    data["n_sims"] = max(100, min(10000, data.get("n_sims", 1000)))
    data["horizon_months"] = max(6, min(60, data.get("horizon_months", 18)))

    # Financial
    fm = data.get("financial_model", {})
    fm["burn_volatility"] = max(0.0, min(1.0, fm.get("burn_volatility", 0.1)))

    # Opportunity
    om = data.get("opportunity_model", {})
    om["growth_rate_sigma"] = max(0.01, min(1.0, om.get("growth_rate_sigma", 0.08)))
    om["setback_prob_monthly"] = max(0.0, min(0.5, om.get("setback_prob_monthly", 0.03)))
    om["setback_impact"] = max(0.0, min(1.0, om.get("setback_impact", 0.5)))

    # Alternative
    am = data.get("alternative_model", {})
    am["reentry_time_months_mu"] = max(0.5, min(24.0, am.get("reentry_time_months_mu", 3.0)))
    am["reentry_time_months_sigma"] = max(0.1, min(12.0, am.get("reentry_time_months_sigma", 1.5)))
    am["value_impact_pct"] = max(-0.5, min(0.5, am.get("value_impact_pct", -0.05)))

    # Wellbeing — also normalize 1-10 scale to 0-1
    wb = data.get("wellbeing_model", {})
    for key, default in [("base_stress", 0.3), ("cash_stress_weight", 0.4),
                         ("progress_stress_weight", 0.3), ("time_pressure_weight", 0.3),
                         ("burnout_threshold", 0.8), ("recovery_rate", 0.05)]:
        v = wb.get(key, default)
        if v > 1.0:
            v = v / 10.0
        ub = 0.5 if key == "recovery_rate" else 1.0
        wb[key] = max(0.0, min(ub, v))


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM_PROMPT = """You are presenting Monte Carlo simulation results for a major life decision.

Rules:
- NEVER be prescriptive. Never say "you should" or "I recommend"
- Present distributions and probabilities, not point estimates
- Highlight what assumptions drive the results
- Be honest about uncertainty and model limitations
- Use clear, accessible language

You MUST produce TWO sections:
1. "brief": A Decision Brief with max 12 lines total:
   - headline: one punchy sentence summarizing the outlook
   - top_insights: exactly 3 bullet points (most important findings)
   - key_risks: exactly 3 bullet points
   - key_levers: exactly 3 things that would most change the outcome
   - what_would_change: one short paragraph

2. "details": Full markdown analysis with sections: Overview, Key Findings, Risk Factors, Sensitivity Insights, Model Limitations

Return ONLY valid JSON:
{"brief":{"headline":"...","top_insights":["...","...","..."],"key_risks":["...","...","..."],"key_levers":["...","...","..."],"what_would_change":"..."},"details":"..."}"""


def synthesize_results(
    client: OpenAI,
    model: str,
    intake_profile: IntakeProfile,
    research_brief: ResearchBrief,
    sim_results_dict: dict,
    template: DecisionTemplate,
) -> dict:
    """Generate structured synthesis of simulation results."""
    prompt = f"""Here are the Monte Carlo simulation results for a "{template.decision_type}" decision:

INTAKE PROFILE:
{intake_profile.model_dump_json(indent=2)}

RESEARCH BRIEF:
{research_brief.model_dump_json(indent=2)}

SIMULATION RESULTS:
Outcome Probabilities: {json.dumps(sim_results_dict.get('outcome_probabilities', {}), indent=2)}
Node KPIs: {json.dumps(sim_results_dict.get('node_kpis', {}), indent=2)}
Sensitivity Analysis: {json.dumps(sim_results_dict.get('sensitivity', {}), indent=2)}

Factor labels: {json.dumps(template.factor_labels)}

Please provide a structured analysis with both a concise brief and detailed breakdown."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
    )
    return _parse_json(response.choices[0].message.content)
