"""Continuous Update Agent - monitors repository for changes (Bedrock version)."""

import subprocess
from pathlib import Path
from dataclasses import dataclass

from doc_pipeline_bedrock.agents.base import BaseAgent
from doc_pipeline_bedrock.models import AgentOutput


@dataclass
class ChangeDetection:
    """Represents detected changes in the repository."""
    changed_files: list[str]
    change_type: str
    impacted_modules: list[str]
    is_high_risk: bool


class ContinuousUpdateAgent(BaseAgent):
    """Monitors repository for changes and determines what needs re-documentation."""

    @property
    def name(self) -> str:
        return "Continuous Update Agent"

    def execute(self, repo_path: str, last_commit: str = None, **kwargs) -> AgentOutput:
        """Detect changes and determine impacted documentation sections."""
        repo = Path(repo_path)
        changes = self._detect_changes(repo, last_commit)

        if not changes.changed_files:
            return self._build_output(
                content="No changes detected. Documentation is up to date.",
                metadata={"needs_update": False},
            )

        summary = self._build_change_summary(changes)

        return self._build_output(
            content=summary,
            metadata={
                "needs_update": True,
                "changed_files": changes.changed_files,
                "impacted_modules": changes.impacted_modules,
                "is_high_risk": changes.is_high_risk,
                "change_type": changes.change_type,
            },
        )

    def _detect_changes(self, repo: Path, last_commit: str = None) -> ChangeDetection:
        """Detect file changes since last documented commit."""
        changed_files = []

        try:
            if last_commit:
                result = subprocess.run(
                    ["git", "diff", "--name-only", last_commit, "HEAD"],
                    cwd=str(repo),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            else:
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                    cwd=str(repo),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            if result.returncode == 0:
                changed_files = [f for f in result.stdout.strip().split("\n") if f]

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        impacted_modules = self._identify_impacted_modules(changed_files)
        is_high_risk = self._assess_risk(changed_files)

        return ChangeDetection(
            changed_files=changed_files,
            change_type="commit",
            impacted_modules=impacted_modules,
            is_high_risk=is_high_risk,
        )

    def _identify_impacted_modules(self, changed_files: list[str]) -> list[str]:
        """Identify which documentation modules are impacted."""
        modules = set()
        for file_path in changed_files:
            parts = Path(file_path).parts
            if len(parts) > 1:
                modules.add(parts[0])
        return sorted(modules)

    def _assess_risk(self, changed_files: list[str]) -> bool:
        """Assess if changes are high-risk for documentation accuracy."""
        high_risk_patterns = [
            "api", "schema", "model", "interface", "config",
            "migration", "route", "endpoint", "contract",
        ]
        for file_path in changed_files:
            lower = file_path.lower()
            if any(pattern in lower for pattern in high_risk_patterns):
                return True
        return False

    def _build_change_summary(self, changes: ChangeDetection) -> str:
        """Build a human-readable summary of detected changes."""
        lines = [
            f"## Change Detection Report",
            f"",
            f"**Change type:** {changes.change_type}",
            f"**Files changed:** {len(changes.changed_files)}",
            f"**Impacted modules:** {', '.join(changes.impacted_modules) or 'None identified'}",
            f"**High-risk changes:** {'Yes' if changes.is_high_risk else 'No'}",
            f"",
            f"### Changed Files",
        ]
        for f in changes.changed_files[:20]:
            lines.append(f"- {f}")
        if len(changes.changed_files) > 20:
            lines.append(f"- ... and {len(changes.changed_files) - 20} more")

        return "\n".join(lines)
