"""Model Watch: offline MLOps monitoring for a churn model.

Pipeline: generated data → trained model → versioned registry → simulated
production stream → drift detection (PSI / KS / concept trend) → alerts →
Flask dashboard. No API keys, no network, fully deterministic.
"""

__version__ = "1.0.0"