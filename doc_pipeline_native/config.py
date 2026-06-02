"""Configuration management for the documentation pipeline.

Layered configuration with deterministic precedence:
    hardcoded defaults  <  YAML file  <  environment variables  <  CLI overrides
"""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.3
    max_tokens: int = 4000


@dataclass
class EnrichmentConfig:
    """Configuration for the context enrichment agent."""
    sources: list[str] = field(default_factory=list)


@dataclass
class VerificationConfig:
    """Configuration for the verification agent."""
    confidence_threshold: float = 0.7
    flag_for_review: bool = True


@dataclass
class SchedulingConfig:
    """Configuration for the continuous update agent."""
    trigger: str = "on_pr_merge"  # "on_pr_merge", "on_release", "scheduled"
    scope: str = "changed_modules"  # "changed_modules", "full"
    cron: Optional[str] = None  # cron expression for scheduled trigger


def _to_bool(value: Any) -> bool:
    """Parse common boolean string forms used in env vars and CLI."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


# Maps environment variable names to dotted config paths and casters.
# Adding a new env-overridable setting? Just add an entry here.
_ENV_MAP: dict[str, tuple[str, Any]] = {
    "OPENAI_API_KEY": ("llm.api_key", str),
    "DOC_PIPELINE_MODEL": ("llm.model", str),
    "DOC_PIPELINE_BASE_URL": ("llm.base_url", str),
    "DOC_PIPELINE_TEMPERATURE": ("llm.temperature", float),
    "DOC_PIPELINE_MAX_TOKENS": ("llm.max_tokens", int),
    "DOC_PIPELINE_CONFIDENCE_THRESHOLD": ("verification.confidence_threshold", float),
    "DOC_PIPELINE_FLAG_FOR_REVIEW": ("verification.flag_for_review", _to_bool),
    "DOC_PIPELINE_TRIGGER": ("scheduling.trigger", str),
    "DOC_PIPELINE_SCOPE": ("scheduling.scope", str),
    "DOC_PIPELINE_CRON": ("scheduling.cron", str),
    "DOC_PIPELINE_OUTPUT_FORMAT": ("output_format", str),
    "DOC_PIPELINE_TEMPLATE": ("template", str),
}


def _set_dotted(obj: Any, key: str, value: Any) -> None:
    """Set a nested attribute by dotted path, e.g. 'llm.model'."""
    parts = key.split(".")
    target = obj
    for part in parts[:-1]:
        target = getattr(target, part)
    setattr(target, parts[-1], value)


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    enrichment: EnrichmentConfig = field(default_factory=EnrichmentConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    scheduling: SchedulingConfig = field(default_factory=SchedulingConfig)
    output_format: str = "markdown"
    template: str = "default"

    @classmethod
    def load(
        cls,
        config_path: Optional[str] = None,
        env: Optional[dict] = None,
        cli_overrides: Optional[dict] = None,
    ) -> "PipelineConfig":
        """Build a config by layering: defaults < YAML < env < CLI.

        Args:
            config_path: Optional path to a YAML config file.
            env: Environment variable mapping (defaults to ``os.environ``).
            cli_overrides: Dict of dotted-path overrides, e.g.
                ``{"llm.model": "gpt-4o", "verification.confidence_threshold": 0.8}``.
                Keys whose value is ``None`` are ignored, so callers can pass
                argparse Namespace values directly.

        Returns:
            A fully-resolved ``PipelineConfig``.
        """
        config = cls.from_yaml(config_path) if config_path else cls()

        env = env if env is not None else os.environ
        config._apply(cls._env_overrides(env))

        if cli_overrides:
            config._apply(cli_overrides)

        return config

    def _apply(self, overrides: dict) -> None:
        """Apply a dict of dotted-path overrides in place; ``None`` values are skipped."""
        for key, value in overrides.items():
            if value is None:
                continue
            _set_dotted(self, key, value)

    @staticmethod
    def _env_overrides(env: dict) -> dict:
        """Extract overrides from environment variables defined in ``_ENV_MAP``."""
        overrides: dict = {}
        for var_name, (path, caster) in _ENV_MAP.items():
            raw = env.get(var_name)
            if raw is None or raw == "":
                continue
            try:
                overrides[path] = caster(raw)
            except (TypeError, ValueError):
                # Silently ignore malformed env values rather than crashing the run.
                continue
        return overrides

    @classmethod
    def from_yaml(cls, path: str) -> "PipelineConfig":
        """Load configuration from a YAML file. Missing files yield defaults."""
        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        llm_data = data.get("pipeline", {})
        enrichment_data = data.get("enrichment", {})
        verification_data = data.get("verification", {})
        scheduling_data = data.get("scheduling", {})
        documentation_data = data.get("documentation", {})

        return cls(
            llm=LLMConfig(
                model=llm_data.get("model", LLMConfig.model),
                api_key=llm_data.get("api_key"),
                base_url=llm_data.get("base_url", LLMConfig.base_url),
                temperature=llm_data.get("temperature", LLMConfig.temperature),
                max_tokens=llm_data.get("max_tokens", LLMConfig.max_tokens),
            ),
            enrichment=EnrichmentConfig(
                sources=enrichment_data.get("sources", []),
            ),
            verification=VerificationConfig(
                confidence_threshold=verification_data.get(
                    "confidence_threshold", VerificationConfig.confidence_threshold
                ),
                flag_for_review=verification_data.get(
                    "flag_for_review", VerificationConfig.flag_for_review
                ),
            ),
            scheduling=SchedulingConfig(
                trigger=scheduling_data.get("trigger", SchedulingConfig.trigger),
                scope=scheduling_data.get("scope", SchedulingConfig.scope),
                cron=scheduling_data.get("cron"),
            ),
            output_format=documentation_data.get("output_format", cls.output_format),
            template=documentation_data.get("template", cls.template),
        )
