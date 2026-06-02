"""Refinement Agent - improves clarity and readability of documentation (Bedrock)."""

from doc_pipeline_bedrock.agents.base import BaseAgent
from doc_pipeline_bedrock.models import AgentOutput


SYSTEM_PROMPT = """You are a documentation refinement agent. Your job is to improve the clarity 
and readability of technical documentation without changing its meaning or adding new information.

Rules:
- Improve sentence structure, flow, and readability.
- Make documentation accessible to both new developers and senior engineers.
- Do NOT add new technical claims or assumptions.
- Do NOT remove any factual content.
- Preserve all section headers and structure.
- Keep code examples and technical terms accurate.
- Use clear, concise language - avoid jargon where simpler terms work."""

USER_PROMPT_TEMPLATE = """Rewrite the following documentation to improve clarity and readability.

**Target audiences:**
- New developers joining the team who need onboarding context
- Senior engineers who need quick reference material

**Documentation to refine:**
{documentation}

**Instructions:**
1. Simplify complex sentences without losing meaning.
2. Add brief transitions between sections for better flow.
3. Ensure consistent formatting and terminology.
4. Break long paragraphs into digestible chunks.
5. Do NOT add new assumptions or technical claims.
"""


class RefinementAgent(BaseAgent):
    """Improves clarity, readability, and usability of documentation."""

    @property
    def name(self) -> str:
        return "Refinement Agent"

    def execute(self, documentation: str, **kwargs) -> AgentOutput:
        """Refine documentation for clarity and readability."""
        user_prompt = USER_PROMPT_TEMPLATE.format(documentation=documentation)

        response = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,
        )

        return self._build_output(
            content=response,
            metadata={"refinement_applied": True},
        )
