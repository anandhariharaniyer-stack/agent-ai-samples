"""CLI entry point for the documentation pipeline.

Configuration precedence (lowest to highest):
    hardcoded defaults  <  --config YAML file  <  environment variables  <  CLI flags

Any CLI flag whose value is left unset (``None``) does not override the layer below it.
"""

import argparse
import logging
import sys

from doc_pipeline_native.orchestrator import DocumentationOrchestrator
from doc_pipeline_native.config import PipelineConfig


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Multi-Agent Documentation Pipeline. "
            "Settings resolve from defaults, then --config YAML, then env vars, "
            "then CLI flags (CLI wins)."
        )
    )

    # Per-run arguments (not in YAML; CLI-only).
    parser.add_argument("repo_path", help="Path to the source code repository")
    parser.add_argument("--output", "-o", default="./generated_docs", help="Output directory")
    parser.add_argument(
        "--config", "-c", help="Path to pipeline config YAML (optional)"
    )
    parser.add_argument(
        "--knowledge", "-k", nargs="*", default=[],
        help="Knowledge source paths (overrides enrichment.sources for this run)",
    )
    parser.add_argument(
        "--last-commit", help="Last documented commit (for incremental updates)"
    )
    parser.add_argument(
        "--generation-only", action="store_true", help="Run only the generation agent"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    # Settings that mirror YAML/env. Default=None means "do not override the layer below".
    parser.add_argument("--api-key", default=None, help="LLM API key (or set OPENAI_API_KEY)")
    parser.add_argument("--model", default=None, help="LLM model name")
    parser.add_argument("--base-url", default=None, help="LLM API base URL")
    parser.add_argument("--temperature", type=float, default=None, help="LLM sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=None, help="LLM max output tokens")
    parser.add_argument(
        "--confidence-threshold", type=float, default=None,
        help="Verification confidence threshold (0.0-1.0)",
    )
    parser.add_argument(
        "--trigger", default=None,
        choices=["on_pr_merge", "on_release", "scheduled"],
        help="Continuous-update trigger",
    )
    parser.add_argument(
        "--scope", default=None,
        choices=["changed_modules", "full"],
        help="What to regenerate on each run",
    )
    parser.add_argument("--output-format", default=None, help="Output format (e.g. markdown)")
    parser.add_argument("--template", default=None, help="Documentation template name")

    return parser


def _cli_overrides(args: argparse.Namespace) -> dict:
    """Map argparse args onto dotted config paths. ``None`` entries are ignored downstream."""
    return {
        "llm.api_key": args.api_key,
        "llm.model": args.model,
        "llm.base_url": args.base_url,
        "llm.temperature": args.temperature,
        "llm.max_tokens": args.max_tokens,
        "verification.confidence_threshold": args.confidence_threshold,
        "scheduling.trigger": args.trigger,
        "scheduling.scope": args.scope,
        "output_format": args.output_format,
        "template": args.template,
    }


def main():
    args = _build_parser().parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s")

    config = PipelineConfig.load(
        config_path=args.config,
        cli_overrides=_cli_overrides(args),
    )

    if not config.llm.api_key:
        print(
            "Error: No API key resolved. Provide --api-key, set OPENAI_API_KEY, "
            "or put 'pipeline.api_key' in your config YAML.",
            file=sys.stderr,
        )
        sys.exit(1)

    orchestrator = DocumentationOrchestrator(
        repo_path=args.repo_path,
        knowledge_sources=args.knowledge or config.enrichment.sources,
        output_dir=args.output,
        config=config,
    )

    if args.generation_only:
        result = orchestrator.run_generation_only()
    else:
        result = orchestrator.run(last_commit=args.last_commit)

    print(f"\n{'='*60}")
    print(f"Documentation Pipeline Complete")
    print(f"{'='*60}")
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
