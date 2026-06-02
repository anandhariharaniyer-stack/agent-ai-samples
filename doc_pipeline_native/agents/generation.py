"""Documentation Generation Agent - produces first-pass documentation from code (Bedrock)."""

from pathlib import Path

from doc_pipeline_bedrock.agents.base import BaseAgent
from doc_pipeline_bedrock.models import AgentOutput


SYSTEM_PROMPT = """You are a documentation generation agent. Your job is to analyze source code 
and produce structured technical documentation. Be thorough but factual - only document what 
you can verify from the code. Do not speculate or add assumptions."""

USER_PROMPT_TEMPLATE = """Analyze the following codebase and generate documentation using this template:

## System Overview
(High-level description of what this system does)

## Key Components
(List and describe main modules, classes, and their responsibilities)

## Data Flow
(How data moves through the system - inputs, processing, outputs)

## External Dependencies
(Third-party libraries, APIs, services, databases)

## Known Constraints
(Limitations, assumptions, or technical debt visible in the code)

---

**Repository structure:**
{repo_structure}

**Source files:**
{source_content}

**README (if available):**
{readme_content}
"""


class GenerationAgent(BaseAgent):
    """Scans source code and produces structured first-draft documentation."""

    @property
    def name(self) -> str:
        return "Documentation Generation Agent"

    def execute(self, repo_path: str, **kwargs) -> AgentOutput:
        """Generate documentation from the repository."""
        repo = Path(repo_path)
        repo_structure = self._get_repo_structure(repo)
        source_content = self._read_source_files(repo)
        readme_content = self._read_readme(repo)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            repo_structure=repo_structure,
            source_content=source_content,
            readme_content=readme_content,
        )

        response = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        return self._build_output(
            content=response,
            metadata={
                "repo_path": repo_path,
                "files_scanned": len(list(repo.rglob("*"))),
            },
        )

    def _get_repo_structure(self, repo: Path) -> str:
        """Get a tree-like representation of the repository structure."""
        lines = []
        extensions = {".py", ".js", ".ts", ".java", ".cs", ".go", ".rs", ".rb", ".yaml", ".yml", ".json"}

        for path in sorted(repo.rglob("*")):
            if any(part.startswith(".") for part in path.parts):
                continue
            if path.is_file() and path.suffix in extensions:
                relative = path.relative_to(repo)
                lines.append(str(relative))

        return "\n".join(lines[:100])

    def _read_source_files(self, repo: Path, max_files: int = 20, max_chars: int = 50000) -> str:
        """Read source files from the repository."""
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
                    header = f"\n--- File: {path.relative_to(repo)} ---\n"
                    content_parts.append(header + text[:5000])
                    total_chars += len(text[:5000])

                    if len(content_parts) >= max_files or total_chars >= max_chars:
                        break
                except (PermissionError, OSError):
                    continue

        return "\n".join(content_parts)

    def _read_readme(self, repo: Path) -> str:
        """Read the README file if it exists."""
        for name in ["README.md", "README.rst", "README.txt", "README"]:
            readme_path = repo / name
            if readme_path.exists():
                return readme_path.read_text(encoding="utf-8", errors="ignore")[:5000]
        return "(No README found)"
