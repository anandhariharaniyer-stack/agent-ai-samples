"""Documentation Pipeline Orchestrator - AWS Bedrock implementation."""

import logging
from datetime import datetime
from pathlib import Path

from doc_pipeline_bedrock.config import PipelineConfig
from doc_pipeline_bedrock.llm_client import BedrockLLMClient
from doc_pipeline_bedrock.models import PipelineResult, Issue, ConfidenceScore
from doc_pipeline_bedrock.agents.generation import GenerationAgent
from doc_pipeline_bedrock.agents.enrichment import EnrichmentAgent
from doc_pipeline_bedrock.agents.verification import VerificationAgent
from doc_pipeline_bedrock.agents.refinement import RefinementAgent
from doc_pipeline_bedrock.agents.continuous import ContinuousUpdateAgent

logger = logging.getLogger(__name__)


class DocumentationOrchestrator:
    """Orchestrates the multi-agent documentation pipeline using AWS Bedrock.

    Coordinates the flow between agents:
    1. Generation → 2. Enrichment → 3. Verification → 4. Refinement

    Optionally runs the Continuous Update Agent to detect changes first.
    """

    def __init__(
        self,
        repo_path: str,
        knowledge_sources: list[str] = None,
        output_dir: str = "./generated_docs",
        config: PipelineConfig = None,
        config_path: str = None,
    ):
        self.repo_path = repo_path
        self.knowledge_sources = knowledge_sources or []
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load config
        if config:
            self.config = config
        elif config_path:
            self.config = PipelineConfig.from_yaml(config_path)
        else:
            self.config = PipelineConfig()

        # Initialize Bedrock LLM client
        self.llm_client = BedrockLLMClient(self.config.bedrock)

        # Initialize agents
        self.generation_agent = GenerationAgent(self.llm_client)
        self.enrichment_agent = EnrichmentAgent(self.llm_client)
        self.verification_agent = VerificationAgent(self.llm_client)
        self.refinement_agent = RefinementAgent(self.llm_client)
        self.continuous_agent = ContinuousUpdateAgent(self.llm_client)

    def run(self, last_commit: str = None, skip_enrichment: bool = False) -> PipelineResult:
        """Run the full documentation pipeline.

        Args:
            last_commit: Optional last documented commit hash (for incremental updates).
            skip_enrichment: Skip enrichment if no knowledge sources available.

        Returns:
            PipelineResult with final documentation and metadata.
        """
        started_at = datetime.now()
        agent_outputs = []

        logger.info("Starting documentation pipeline (Bedrock)...")
        logger.info(f"  Model: {self.config.bedrock.model_id}")
        logger.info(f"  Region: {self.config.bedrock.region}")

        # Step 0: Check for changes (optional)
        if last_commit:
            logger.info("[0/4] Detecting changes...")
            change_output = self.continuous_agent.execute(
                repo_path=self.repo_path,
                last_commit=last_commit,
            )
            agent_outputs.append(change_output)

            if not change_output.metadata.get("needs_update", True):
                logger.info("No changes detected. Pipeline skipped.")
                return PipelineResult(
                    output_path="",
                    final_documentation="No changes detected. Documentation is up to date.",
                    started_at=started_at,
                    completed_at=datetime.now(),
                    agent_outputs=agent_outputs,
                )

        # Step 1: Generate documentation
        logger.info("[1/4] Generating documentation from codebase...")
        gen_output = self.generation_agent.execute(repo_path=self.repo_path)
        agent_outputs.append(gen_output)
        logger.info(f"  Generated {len(gen_output.content)} chars of documentation")

        # Step 2: Enrich with context
        current_doc = gen_output.content
        if not skip_enrichment and self.knowledge_sources:
            logger.info("[2/4] Enriching with context from knowledge sources...")
            enrich_output = self.enrichment_agent.execute(
                documentation=current_doc,
                knowledge_sources=self.knowledge_sources,
            )
            agent_outputs.append(enrich_output)
            current_doc = enrich_output.content
            logger.info(f"  Enrichment complete. Sources used: {enrich_output.metadata.get('sources_used', 0)}")
        else:
            logger.info("[2/4] Skipping enrichment (no knowledge sources)")

        # Step 3: Verify against code
        logger.info("[3/4] Verifying documentation accuracy...")
        verify_output = self.verification_agent.execute(
            documentation=current_doc,
            repo_path=self.repo_path,
            confidence_threshold=self.config.verification.confidence_threshold,
        )
        agent_outputs.append(verify_output)
        current_doc = verify_output.content

        issues = [Issue(**item) for item in verify_output.metadata.get("issues", [])]
        confidence_scores = [
            ConfidenceScore(**item) for item in verify_output.metadata.get("confidence_scores", [])
        ]
        avg_confidence = verify_output.metadata.get("avg_confidence", 0.0)
        logger.info(f"  Issues found: {len(issues)} | Avg confidence: {avg_confidence:.0%}")

        # Step 4: Refine for readability
        logger.info("[4/4] Refining documentation for readability...")
        refine_output = self.refinement_agent.execute(documentation=current_doc)
        agent_outputs.append(refine_output)
        final_doc = refine_output.content
        logger.info("  Refinement complete")

        # Write output
        output_path = self._write_output(final_doc)
        logger.info(f"Documentation written to: {output_path}")

        return PipelineResult(
            output_path=str(output_path),
            final_documentation=final_doc,
            issues=issues,
            confidence_scores=confidence_scores,
            avg_confidence=avg_confidence,
            agent_outputs=agent_outputs,
            started_at=started_at,
            completed_at=datetime.now(),
        )

    def run_generation_only(self) -> PipelineResult:
        """Run only the generation agent (useful for quick drafts)."""
        started_at = datetime.now()
        gen_output = self.generation_agent.execute(repo_path=self.repo_path)
        output_path = self._write_output(gen_output.content)

        return PipelineResult(
            output_path=str(output_path),
            final_documentation=gen_output.content,
            agent_outputs=[gen_output],
            started_at=started_at,
            completed_at=datetime.now(),
        )

    def run_verification_only(self, documentation: str) -> PipelineResult:
        """Run only the verification agent against existing documentation."""
        started_at = datetime.now()
        verify_output = self.verification_agent.execute(
            documentation=documentation,
            repo_path=self.repo_path,
            confidence_threshold=self.config.verification.confidence_threshold,
        )

        issues = [Issue(**item) for item in verify_output.metadata.get("issues", [])]
        confidence_scores = [
            ConfidenceScore(**item) for item in verify_output.metadata.get("confidence_scores", [])
        ]

        return PipelineResult(
            output_path="",
            final_documentation=verify_output.content,
            issues=issues,
            confidence_scores=confidence_scores,
            avg_confidence=verify_output.metadata.get("avg_confidence", 0.0),
            agent_outputs=[verify_output],
            started_at=started_at,
            completed_at=datetime.now(),
        )

    def _write_output(self, content: str) -> Path:
        """Write documentation to the output directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"documentation_{timestamp}.md"
        output_path = self.output_dir / filename

        output_path.write_text(content, encoding="utf-8")
        return output_path
