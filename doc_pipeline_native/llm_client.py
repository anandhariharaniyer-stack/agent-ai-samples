"""AWS Bedrock LLM client."""

import json
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

from doc_pipeline_bedrock.config import BedrockConfig


class BedrockLLMClient:
    """LLM client using AWS Bedrock runtime."""

    def __init__(self, config: BedrockConfig):
        self.config = config

        # Build boto3 session
        session_kwargs = {}
        if config.profile:
            session_kwargs["profile_name"] = config.profile

        session = boto3.Session(**session_kwargs)

        boto_config = BotoConfig(
            region_name=config.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )

        self.client = session.client("bedrock-runtime", config=boto_config)

    def generate(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None) -> str:
        """Send a prompt to Bedrock and return the response text.

        Supports Anthropic Claude models via the Messages API.
        """
        temp = temperature if temperature is not None else self.config.temperature

        # Use the Converse API (model-agnostic)
        if self._is_claude_model():
            return self._invoke_claude(system_prompt, user_prompt, temp)
        else:
            return self._invoke_converse(system_prompt, user_prompt, temp)

    def _is_claude_model(self) -> bool:
        """Check if the configured model is an Anthropic Claude model."""
        return "anthropic" in self.config.model_id.lower()

    def _invoke_claude(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Invoke Anthropic Claude via Bedrock."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
        }

        response = self.client.invoke_model(
            modelId=self.config.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]

    def _invoke_converse(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Invoke any model via the Bedrock Converse API."""
        response = self.client.converse(
            modelId=self.config.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                }
            ],
            inferenceConfig={
                "maxTokens": self.config.max_tokens,
                "temperature": temperature,
            },
        )

        output_message = response["output"]["message"]
        return output_message["content"][0]["text"]
