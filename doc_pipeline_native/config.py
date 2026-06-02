"""Configuration management for the documentation pipeline (Bedrock version)."""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BedrockConfig:
    """AWS Bedrock provider configuration."""
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    region: str = "us-east-1"
    profile: Optional[str] = None  # AWS profile name (optional)
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
    trigger: str = "on_pr_merge"
    scope: str = "changed_modules"
    cron: Optional[str] = None


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration."""
    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    enrichment: EnrichmentConfig = field(default_factory=EnrichmentConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    scheduling: SchedulingConfig = field(default_factory=SchedulingConfig)
    output_format: str = "markdown"
    template: str = "default"

    @classmethod
    def from_yaml(cls, path: str) -> "PipelineConfig":
        """Load configuration from a YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        bedrock_data = data.get("bedrock", {})
        enrichment_data = data.get("enrichment", {})
        verification_data = data.get("verification", {})
        scheduling_data = data.get("scheduling", {})

        return cls(
            bedrock=BedrockConfig(
                model_id=bedrock_data.get("model_id", "anthropic.claude-3-sonnet-20240229-v1:0"),
                region=bedrock_data.get("region", "us-east-1"),
                profile=bedrock_data.get("profile"),
                temperature=bedrock_data.get("temperature", 0.3),
                max_tokens=bedrock_data.get("max_tokens", 4000),
            ),
            enrichment=EnrichmentConfig(
                sources=enrichment_data.get("sources", []),
            ),
            verification=VerificationConfig(
                confidence_threshold=verification_data.get("confidence_threshold", 0.7),
                flag_for_review=verification_data.get("flag_for_review", True),
            ),
            scheduling=SchedulingConfig(
                trigger=scheduling_data.get("trigger", "on_pr_merge"),
                scope=scheduling_data.get("scope", "changed_modules"),
                cron=scheduling_data.get("cron"),
            ),
            output_format=data.get("documentation", {}).get("output_format", "markdown"),
            template=data.get("documentation", {}).get("template", "default"),
        )
