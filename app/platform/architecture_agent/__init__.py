"""Platform-aware architecture decision support for the registered Architect Agent."""

from app.platform.architecture_agent.service import create_architecture_decision
from app.platform.architecture_agent.validator import validate_architecture_decision

__all__ = ["create_architecture_decision", "validate_architecture_decision"]
