"""CLI entry point for the documentation pipeline (Bedrock version)."""

import argparse
import logging
import sys

from doc_pipeline_bedrock.orchestrator import DocumentationOrchestrator
from doc_pipeline_bedrock.config import PipelineConfig, BedrockConfig


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Documentation Pipeline (AWS Bedrock)")
    parser.add_argument("repo_path", help="Path to the source code repository")
    parser.add_argument("--output", "-o", default="./generated_docs", help="Output directory")
    parser.add_argument("--config", "-c", help="Path to pipeline config YAML")
    parser.add_argument("--knowledge", "-k", nargs="*", default=[], help="Knowledge source paths")
    parser.add_argument(
        "--model-id",
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        help="Bedrock model ID",
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", help="AWS profile name (optional)")
    parser.add_argument("--last-commit", help="Last documented commit (for incremental updates)")
    parser.add_argument("--generation-only", action="store_true", help="Run only the generation agent")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    # Build config
    if args.config:
        config = PipelineConfig.from_yaml(args.config)
    else:
        config = PipelineConfig(
            bedrock=BedrockConfig(
                model_id=args.model_id,
                region=args.region,
                profile=args.profile,
            )
        )

    # Run pipeline
    try:
        orchestrator = DocumentationOrchestrator(
            repo_path=args.repo_path,
            knowledge_sources=args.knowledge,
            output_dir=args.output,
            config=config,
        )
    except Exception as e:
        print(f"Error initializing Bedrock client: {e}")
        print("Ensure AWS credentials are configured (via profile, env vars, or IAM role).")
        sys.exit(1)

    if args.generation_only:
        result = orchestrator.run_generation_only()
    else:
        result = orchestrator.run(last_commit=args.last_commit)

    # Print results
    print(f"\n{'='*60}")
    print(f"Documentation Pipeline Complete (Bedrock)")
    print(f"{'='*60}")
    print(f"Model: {config.bedrock.model_id}")
    print(f"Region: {config.bedrock.region}")
    print(f"Output: {result.output_path}")
    print(f"Duration: {(result.completed_at - result.started_at).total_seconds():.1f}s")
    print(f"Average Confidence: {result.avg_confidence:.0%}")
    print(f"Issues Found: {len(result.issues)}")

    if result.issues:
        print(f"\n{'─'*60}")
        print("Issues:")
        for issue in result.issues:
            print(f"  [{issue.severity.upper()}] {issue.section}: {issue.description}")
            if issue.suggestion:
                print(f"         → {issue.suggestion}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
