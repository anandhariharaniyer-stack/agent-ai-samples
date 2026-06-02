# doc_pipeline_native

Multi-agent documentation pipeline using any OpenAI-compatible LLM (OpenAI, Azure OpenAI, local LLMs via LiteLLM, etc.).

- Zero external dependencies beyond `pyyaml` (uses `urllib` for HTTP)
- Lightweight and portable
- Works with any provider that exposes the OpenAI Chat Completions API

## Project Layout

```
doc_pipeline_native/
├── __init__.py            # Package exports
├── main.py                # CLI entry point
├── orchestrator.py        # Pipeline orchestrator (coordinates agents)
├── config.py              # Configuration management (YAML-based)
├── llm_client.py          # LLM provider client
├── models.py              # Data models (Issue, AgentOutput, PipelineResult)
├── pipeline_config.yaml   # Example configuration
└── agents/
    ├── base.py            # Abstract base agent class
    ├── generation.py      # Agent 1: Generate docs from code
    ├── enrichment.py      # Agent 2: Add business/architectural context
    ├── verification.py    # Agent 3: Validate accuracy against code
    ├── refinement.py      # Agent 4: Improve clarity and readability
    └── continuous.py      # Agent 5: Detect changes, trigger re-runs
```

## Install

```bash
pip install pyyaml
export OPENAI_API_KEY="sk-..."
```

Run from the repo root so the `doc_pipeline_native` package is importable.

## CLI

Run the full pipeline:

```bash
python -m doc_pipeline_native.main /path/to/your/repo \
  --output ./generated_docs \
  --knowledge ./docs/architecture.md ./docs/business-context.md \
  --verbose
```

Run generation only (quick draft, skips verification/refinement):

```bash
python -m doc_pipeline_native.main /path/to/your/repo --generation-only
```

Run with a config file:

```bash
python -m doc_pipeline_native.main /path/to/your/repo \
  --config doc_pipeline_native/pipeline_config.yaml
```

## Library

```python
from doc_pipeline_native import DocumentationOrchestrator, PipelineConfig
from doc_pipeline_native.config import LLMConfig

config = PipelineConfig(
    llm=LLMConfig(
        model="gpt-4",
        api_key="sk-...",
        base_url="https://api.openai.com/v1",
    )
)

orchestrator = DocumentationOrchestrator(
    repo_path="./my-project",
    knowledge_sources=["./docs/architecture.md"],
    output_dir="./generated_docs",
    config=config,
)

result = orchestrator.run()
print(f"Output: {result.output_path}")
print(f"Confidence: {result.avg_confidence:.0%}")
print(f"Issues: {len(result.issues)}")
```

## Incremental Updates

Pass `last_commit` to only regenerate docs for changed modules:

```python
result = orchestrator.run(last_commit="abc123f")
```

Or via CLI:

```bash
python -m doc_pipeline_native.main ./repo --last-commit abc123f
```

## Configuration

Settings are resolved in this order, lowest to highest priority:

```
hardcoded defaults  <  --config YAML  <  environment variables  <  CLI flags
```

A CLI flag left unset (its `argparse` default is `None`) does **not** override the layer below it. So `--config x.yaml --model gpt-4o` will load `x.yaml` and then override the model — no silent overrides either way.

### Settings reference

| Setting | YAML path | Env var | CLI flag |
|---|---|---|---|
| API key | `pipeline.api_key` | `OPENAI_API_KEY` | `--api-key` |
| Model | `pipeline.model` | `DOC_PIPELINE_MODEL` | `--model` |
| Base URL | `pipeline.base_url` | `DOC_PIPELINE_BASE_URL` | `--base-url` |
| Temperature | `pipeline.temperature` | `DOC_PIPELINE_TEMPERATURE` | `--temperature` |
| Max tokens | `pipeline.max_tokens` | `DOC_PIPELINE_MAX_TOKENS` | `--max-tokens` |
| Confidence threshold | `verification.confidence_threshold` | `DOC_PIPELINE_CONFIDENCE_THRESHOLD` | `--confidence-threshold` |
| Flag for review | `verification.flag_for_review` | `DOC_PIPELINE_FLAG_FOR_REVIEW` | *(YAML/env only)* |
| Trigger | `scheduling.trigger` | `DOC_PIPELINE_TRIGGER` | `--trigger` |
| Scope | `scheduling.scope` | `DOC_PIPELINE_SCOPE` | `--scope` |
| Cron | `scheduling.cron` | `DOC_PIPELINE_CRON` | *(YAML/env only)* |
| Output format | `documentation.output_format` | `DOC_PIPELINE_OUTPUT_FORMAT` | `--output-format` |
| Template | `documentation.template` | `DOC_PIPELINE_TEMPLATE` | `--template` |
| Enrichment sources | `enrichment.sources` | *(none)* | `--knowledge` |

Per-run-only flags (not in YAML): `--output`, `--last-commit`, `--generation-only`, `--verbose`.

### Tuning notes

| Setting | Notes |
|---|---|
| `temperature` | Lower (0.1–0.3) for verification, higher (0.3–0.5) for generation/refinement |
| `confidence_threshold` | Sections below this score get flagged for human review |
| `trigger` | When to re-run the pipeline (`on_pr_merge`, `on_release`, `scheduled`) |
| `scope` | What to regenerate (`changed_modules` for incremental, `full` for everything) |

See [`pipeline_config.yaml`](./pipeline_config.yaml) for a worked example.

## Companion

For the AWS Bedrock variant of the same pipeline, see [`../doc_pipeline_bedrock/`](../doc_pipeline_bedrock/).
