from dataclasses import dataclass, field


@dataclass
class SimState:
    """Per-simulation mutable state tracked each month."""
    month: int = 0
    cash_balance: float = 0.0
    opportunity_progress: float = 0.0
    setback_count: int = 0
    alternative_cost: float = 0.0
    stress_index: float = 0.3
    burned_out: bool = False
    ran_out: bool = False
    opportunity_failed: bool = False
    opportunity_succeeded: bool = False


@dataclass
class SimTrace:
    """Recorded time-series for one simulation run."""
    cash: list[float] = field(default_factory=list)
    opportunity: list[float] = field(default_factory=list)
    stress: list[float] = field(default_factory=list)
    runway_month: int | None = None  # month cash hit 0, or None
    outcome: str = ""  # classified after simulation ends
