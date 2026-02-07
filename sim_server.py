"""Simulation server for Mosaic Mind.

Flask server on port 5001 that runs Monte Carlo simulations
using the Dedalus SDK for tool orchestration.
"""
from __future__ import annotations
import asyncio
import json
import logging

from flask import Flask, request, jsonify
from flask_cors import CORS
from dedalus_labs import AsyncDedalus, DedalusRunner

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_simulation_tool(api_key: str, model: str):
    """Create a simulation tool function with the given API credentials."""

    def run_simulation(decision_context: str, intake_answers: str) -> str:
        """Run a comprehensive Monte Carlo simulation for a major life decision.

        Analyzes the decision by running 1000 simulated scenarios across four dimensions:
        financial survival, opportunity progress, alternative costs, and wellbeing/stress.
        Returns detailed outcome probabilities, key insights, risks, and recommendations.

        Args:
            decision_context: Full description of the decision being analyzed
            intake_answers: JSON string with keys q1-q5 containing answers to simulation intake questions

        Returns:
            JSON string with simulation synthesis including outcome probabilities, insights, risks, and levers
        """
        from openai import OpenAI as OAIClient
        import sim_llm
        from sim.engine import run_monte_carlo
        from sim.sensitivity import run_sensitivity as run_sens
        from sim_schemas import IntakeProfile

        client = OAIClient(api_key=api_key, base_url="https://api.dedaluslabs.ai/v1")

        # 1. Classify decision
        template = sim_llm.classify_decision(client, model, decision_context)

        # 2. Build intake profile
        answers = json.loads(intake_answers) if isinstance(intake_answers, str) else intake_answers
        profile = IntakeProfile(
            decision_type=template.decision_type,
            factors=template.factors,
            q1=answers.get('q1', ''),
            q2=answers.get('q2', ''),
            q3=answers.get('q3', ''),
            q4=answers.get('q4', ''),
            q5=answers.get('q5', ''),
            raw_description=decision_context,
        )

        # 3. Research
        research = sim_llm.run_research(client, model, profile, template)

        # 4. Generate sim config
        sim_config = sim_llm.generate_sim_config(client, model, profile, research, template)

        # 5. Run Monte Carlo (1000 simulations)
        sim_results = run_monte_carlo(sim_config)

        # 6. Sensitivity analysis
        try:
            sensitivity = run_sens(sim_config)
            sim_results.sensitivity = sensitivity
        except Exception:
            pass

        # 7. Synthesize results
        results_dict = sim_results.model_dump()
        synthesis = sim_llm.synthesize_results(client, model, profile, research, results_dict, template)

        return json.dumps({
            'synthesis': synthesis,
            'outcome_probabilities': results_dict['outcome_probabilities'],
            'node_kpis': results_dict['node_kpis'],
            'sensitivity': results_dict.get('sensitivity', {}),
            'factor_labels': template.factor_labels,
        })

    return run_simulation


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route('/simulate', methods=['POST'])
def simulate():
    """Run a Monte Carlo simulation for a decision."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    api_key = data.get('apiKey')
    model = data.get('model', 'anthropic/claude-sonnet-4-20250514')
    decision_context = data.get('decisionContext', '')
    mosaic_exploration = data.get('mosaicExploration', '')
    intake_answers = data.get('intakeAnswers', {})

    if not api_key:
        return jsonify({"error": "apiKey is required"}), 400

    if not decision_context:
        return jsonify({"error": "decisionContext is required"}), 400

    # Create the simulation tool with the user's API key
    sim_tool = create_simulation_tool(api_key, model)

    # Build the prompt for the Dedalus runner
    prompt = f"""You are a decision analysis assistant with access to a Monte Carlo simulation tool.

DECISION: {decision_context}

EXPLORATION CONTEXT (from decision tree analysis):
{mosaic_exploration}

SIMULATION INTAKE ANSWERS:
{json.dumps(intake_answers)}

Use the run_simulation tool to analyze this decision. Pass the decision context as the first argument
and the intake answers as a JSON string for the second argument.

After receiving the simulation results, provide a clear summary that:
1. Highlights the key outcome probabilities
2. Explains the top insights and risks
3. Identifies what would change the outcome
4. Integrates findings with the exploration context

Be direct and data-driven. No hedging."""

    try:
        # Try using the Dedalus SDK runner
        client = AsyncDedalus(api_key=api_key)
        runner = DedalusRunner(client=client)

        result = asyncio.run(
            runner.run(input=prompt, model=model, tools=[sim_tool])
        )

        return jsonify({"result": result.final_output})

    except Exception as e:
        logger.warning(f"Dedalus runner failed, falling back to direct execution: {e}")

        # Fallback: run the simulation tool directly
        try:
            raw_result = sim_tool(decision_context, json.dumps(intake_answers))
            return jsonify({"result": json.loads(raw_result)})
        except Exception as fallback_error:
            logger.error(f"Fallback simulation also failed: {fallback_error}")
            return jsonify({"error": str(fallback_error)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
