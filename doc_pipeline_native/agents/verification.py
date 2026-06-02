"""Verification Agent - validates documentation accuracy against code (Bedrock)."""

import json
from pathlib import Path

from doc_pipeline_bedrock.agents.base import BaseAgent
from doc_pipeline_bedrock.models import AgentOutput, Issue, ConfidenceScore


SYSTEM_PROMPT = """You are a verification agent. Your job is to validate whether documentation 
accurately reflects the actual codebase. You must be critical and thorough.

You will output a JSON response with this structure:
{
    "issues": [
        {
            "section": "section name",
            "description": "what is wrong or unclear",
            "severity": "high|medium|low",
            "suggestion": "how to fix it"
        }
    ],
    "confidence_scores": [
        {
            "section": "section name",
            "score": 0.0-1.0,
            "reason": "why this score"
        }
    ],
    "verified_documentation": "the documentation with corrections applied"
}"""

USER_PROMPT_TEMPLATE = """Validate whether the following documentation accurately reflects the code.
Identify mismatches, ambiguities, or unverifiable claims.

**Documentation:**
{documentation}

**Codebase (key files):**
{code_content}

**Validation criteria:**
1. Every claim in the documentation must be verifiable from the code.
2. Flag any documentation that describes behavior not present in the code.
3. Flag ambiguous statements that could be interpreted multiple ways.
4. Assign a confidence score (0.0-1.0) to each major section.
5. Apply corrections where possible and return the verified documentation.

Respond ONLY with valid JSON matching the schema described in your system prompt.
"""


class VerificationAgent(BaseAgent):
    """Compares documentation with code and flags mismatches."""

    @property
    def name(self) -> str:
        return "Verification Agent"

    def execute(self, documentation: str, repo_path: str, confidence_threshold: float = 0.7, **kwargs) -> AgentOutput:
        """Verify documentation accuracy against the codebase."""
        repo = Path(repo_path)
        code_content = self._read_key_files(repo)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            documentation=documentation,
            code_content=code_content,
        )

        response = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        issues, confidence_scores, verified_doc = self._parse_response(response, documentation)

        flagged_sections = [
            cs.section for cs in confidence_scores if cs.score < confidence_threshold
        ]

        return self._build_output(
            content=verified_doc,
            metadata={
                "issues": [vars(i) for i in issues],
                "confidence_scores": [vars(cs) for cs in confidence_scores],
                "flagged_sections": flagged_sections,
                "avg_confidence": (
                    sum(cs.score for cs in confidence_scores) / len(confidence_scores)
                    if confidence_scores
                    else 0.0
                ),
            },
        )

    def _parse_response(self, response: str, fallback_doc: str) -> tuple[list[Issue], list[ConfidenceScore], str]:
        """Parse the JSON response from the verification LLM."""
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1]
                clean = clean.rsplit("```", 1)[0]

            data = json.loads(clean)

            issues = [
                Issue(
                    section=item.get("section", "Unknown"),
                    description=item.get("description", ""),
                    severity=item.get("severity", "medium"),
                    suggestion=item.get("suggestion"),
                )
                for item in data.get("issues", [])
            ]

            confidence_scores = [
                ConfidenceScore(
                    section=item.get("section", "Unknown"),
                    score=float(item.get("score", 0.5)),
                    reason=item.get("reason", ""),
                )
                for item in data.get("confidence_scores", [])
            ]

            verified_doc = data.get("verified_documentation", fallback_doc)
            return issues, confidence_scores, verified_doc

        except (json.JSONDecodeError, KeyError, TypeError):
            return (
                [Issue(section="Parser", description="Could not parse verification output", severity="low")],
                [],
                fallback_doc,
            )

    def _read_key_files(self, repo: Path, max_files: int = 15, max_chars: int = 40000) -> str:
        """Read key source files for verification."""
        extensions = {".py", ".js", ".ts", ".java", ".cs", ".go", ".rs", ".rb"}
        content_parts = []
        total_chars = 0

        for path in sorted(repo.rglob("*")):
            if any(part.startswith(".") for part in path.parts):
                continue
            if "node_modules" in path.parts or "venv" in path.parts:
                continue
            if path.is_file() and path.suffix in extensions:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    header = f"\n--- {path.relative_to(repo)} ---\n"
                    content_parts.append(header + text[:4000])
                    total_chars += len(text[:4000])

                    if len(content_parts) >= max_files or total_chars >= max_chars:
                        break
                except (PermissionError, OSError):
                    continue

        return "\n".join(content_parts)
