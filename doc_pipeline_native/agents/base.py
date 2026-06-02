"""Base agent class for the documentation pipeline."""

from abc import ABC, abstractmethod
from datetime import datetime

from doc_pipeline_native.llm_client import LLMClient
from doc_pipeline_native.models import AgentOutput


class BaseAgent(ABC):
    """Abstract base class for all documentation agents."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging and tracking."""
        ...

    @abstractmethod
    def execute(self, **kwargs) -> AgentOutput:
        """Execute the agent's task and return output."""
        ...

    def _build_output(self, content: str, metadata: dict = None) -> AgentOutput:
        """Helper to construct a standardized AgentOutput."""
        return AgentOutput(
            agent_name=self.name,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now(),
        )
