"""Context Enrichment Agent - adds business and architectural context."""

from pathlib import Path

from doc_pipeline_native.agents.base import BaseAgent
from doc_pipeline_native.models import AgentOutput


SYSTEM_PROMPT = """You are a context enrichment agent. Your job is to enhance technical documentation 
by incorporating business context, architectural decisions, and domain knowledge from provided sources.

Rules:
- Only add context that is supported by the provided knowledge sources.
- Highlight assumptions explicitly with [ASSUMPTION] tags.
- Do not invent or hallucinate information not present in the sources.
- Preserve the original structure and technical accuracy of the documentation."""

USER_PROMPT_TEMPLATE = """Enhance the following documentation by incorporating missing business 
and architectural context from the provided knowledge sources.

**Documentation to enhance:**
{documentation}

**Knowledge sources:**
{knowledge_content}

**Instructions:**
1. Add business context where the documentation only describes technical behavior.
2. Include architectural rationale where design decisions are documented without explanation.
3. Tag any assumptions explicitly as [ASSUMPTION: reason].
4. Preserve all existing technical content - only add, never remove.
"""


class EnrichmentAgent(BaseAgent):
    """Adds missing business and architectural context from knowledge sources."""

    @property
    def name(self) -> str:
        return "Context Enrichment Agent"

    def execute(self, documentation: str, knowledge_sources: list[str] = None, **kwargs) -> AgentOutput:
        """Enrich documentation with context from knowledge sources.

        Args:
            documentation: Raw documentation from the generation agent.
            knowledge_sources: List of file paths to knowledge sources.

        Returns:
            AgentOutput containing enriched documentation.
        """
        knowledge_content = self._load_knowledge_sources(knowledge_sources or [])

        if not knowledge_content.strip():
            return self._build_output(
                content=documentation,
                metadata={"enrichment_applied": False, "reason": "No knowledge sources provided"},
            )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            documentation=documentation,
            knowledge_content=knowledge_content,
        )

        response = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return self._build_output(
            content=response,
            metadata={
                "enrichment_applied": True,
                "sources_used": len(knowledge_sources or []),
            },
        )

    def _load_knowledge_sources(self, sources: list[str]) -> str:
        """Load content from knowledge source files."""
        content_parts = []

        for source_path in sources:
            path = Path(source_path)
            if path.is_file():
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    content_parts.append(f"\n--- Source: {path.name} ---\n{text[:10000]}")
                except (PermissionError, OSError):
                    continue
            elif path.is_dir():
                for file in sorted(path.rglob("*.md")):
                    try:
                        text = file.read_text(encoding="utf-8", errors="ignore")
                        content_parts.append(f"\n--- Source: {file.name} ---\n{text[:5000]}")
                    except (PermissionError, OSError):
                        continue

        return "\n".join(content_parts)
