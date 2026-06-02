# doc_pipeline_bedrock

Multi-agent documentation pipeline running on AWS Bedrock.

- Calls Bedrock runtime via `boto3`
- Native support for Claude (Anthropic) via the Messages API
- Works with any Bedrock-hosted model via the Converse API
- Uses IAM authentication (no API keys needed)

## Project Layout

```
doc_pipeline_bedrock/
├── __init__.py            # Package exports
├── main.py                # CLI entry point
├── orchestrator.py        # Pipeline orchestrator (coordinates agents)
├── config.py              # Configuration management (YAML-based)
├── llm_client.py          # Bedrock runtime client
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
pip install boto3 pyyaml
```

Configure AWS credentials via any standard method (named profile, env vars, or IAM role on EC2/Lambda):

```bash
aws configure --profile my-profile
```

Run from the repo root so the `doc_pipeline_bedrock` package is importable.

## CLI

Run the full pipeline:

```bash
python -m doc_pipeline_bedrock.main /path/to/your/repo \
  --output ./generated_docs \
  --region us-east-1 \
  --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
  --verbose
```

Run with a specific AWS profile:

```bash
python -m doc_pipeline_bedrock.main /path/to/your/repo --profile my-aws-profile
```

Run with a config file:

```bash
python -m doc_pipeline_bedrock.main /path/to/your/repo \
  --config doc_pipeline_bedrock/pipeline_config.yaml
```

## Library

```python
from doc_pipeline_bedrock import DocumentationOrchestrator, PipelineConfig
from doc_pipeline_bedrock.config import BedrockConfig

config = PipelineConfig(
    bedrock=BedrockConfig(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        region="us-east-1",
        profile="my-aws-profile",
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

```python
result = orchestrator.run(last_commit="abc123f")
```

Or via CLI:

```bash
python -m doc_pipeline_bedrock.main ./repo --last-commit abc123f
```

## Supported Models

| Model | Model ID |
|---|---|
| Claude 3.5 Sonnet | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| Claude 3 Sonnet   | `anthropic.claude-3-sonnet-20240229-v1:0` |
| Claude 3 Haiku    | `anthropic.claude-3-haiku-20240307-v1:0` |
| Llama 3 70B       | `meta.llama3-70b-instruct-v1:0` |
| Mistral Large     | `mistral.mistral-large-2402-v1:0` |

## Configuration

See [`pipeline_config.yaml`](./pipeline_config.yaml) for the full set of options.

| Setting | Notes |
|---|---|
| `temperature` | Lower (0.1–0.3) for verification, higher (0.3–0.5) for generation/refinement |
| `confidence_threshold` | Sections below this score get flagged for human review |
| `trigger` | When to re-run the pipeline (`on_pr_merge`, `on_release`, `scheduled`) |
| `scope` | What to regenerate (`changed_modules` for incremental, `full` for everything) |

## Companion

For the OpenAI-compatible variant of the same pipeline, see [`../doc_pipeline_native/`](../doc_pipeline_native/).
