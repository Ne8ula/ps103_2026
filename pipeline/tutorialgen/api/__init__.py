"""HTTP data endpoints (FastAPI). ``create_app()`` builds the app; ``python -m tutorialgen serve`` runs it."""

from .app import ApiSettings, create_app
from .jobs import JobManager, RunRecord, RunRequest

__all__ = ["ApiSettings", "JobManager", "RunRecord", "RunRequest", "create_app"]
