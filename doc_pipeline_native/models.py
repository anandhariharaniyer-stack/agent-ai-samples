"""Data models for the documentation pipeline."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Issue:
    """Represents a documentation issue flagged by the verification agent."""
    section: str
    description: str
    severity: str  # "high", "medium", "low"
    suggestion: Optional[str] = None


@dataclass
class ConfidenceScore:
    """Confidence score for a documentation section."""
    section: str
    score: float  # 0.0 to 1.0
    reason: str = ""


@dataclass
class AgentOutput:
    """Output from a single agent execution."""
    agent_name: str
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PipelineResult:
    """Final result of the documentation pipeline."""
    output_path: str
    final_documentation: str
    issues: list[Issue] = field(default_factory=list)
    confidence_scores: list[ConfidenceScore] = field(default_factory=list)
    avg_confidence: float = 0.0
    agent_outputs: list[AgentOutput] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
