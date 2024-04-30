from os import getenv
from typing import Literal

from openai.types.chat.completion_create_params import ResponseFormat

from draive.helpers import getenv_float, getenv_int
from draive.types import Model

__all__ = [
    "OpenAIChatConfig",
    "OpenAIEmbeddingConfig",
    "OpenAIImageGenerationConfig",
]


class OpenAIChatConfig(Model):
    model: (
        Literal[
            "gpt-4-0125-preview",
            "gpt-4-turbo-preview",
            "gpt-4-1106-preview",
            "gpt-4-vision-preview",
            "gpt-4",
            "gpt-4-0314",
            "gpt-4-0613",
            "gpt-4-32k",
            "gpt-4-32k-0314",
            "gpt-4-32k-0613",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-0301",
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-16k-0613",
        ]
        | str
    ) = getenv("OPENAI_MODEL", default="gpt-3.5-turbo-0125")
    temperature: float = getenv_float("OPENAI_TEMPERATURE", 0.0)
    top_p: float | None = None
    frequency_penalty: float | None = None
    max_tokens: int | None = None
    seed: int | None = getenv_int("OPENAI_SEED")
    response_format: ResponseFormat | None = None
    vision_details: Literal["auto", "low", "high"] | None = None
    timeout: float | None = None
    recursion_limit: int = 4


class OpenAIEmbeddingConfig(Model):
    model: (
        Literal[
            "text-embedding-ada-002",
            "text-embedding-3-small",
            "text-embedding-3-large",
        ]
        | str
    ) = "text-embedding-3-small"
    dimensions: int | None = None
    batch_size: int = 32
    encoding_format: Literal["float", "base64"] | None = None
    timeout: float | None = None


class OpenAIImageGenerationConfig(Model):
    model: Literal["dall-e-2", "dall-e-3"] | str = "dall-e-2"
    quality: Literal["standard", "hd"] = "standard"
    size: Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"] = "1024x1024"
    style: Literal["vivid", "natural"] = "vivid"
    timeout: float | None = None
    response_format: Literal["url", "b64_json"] = "b64_json"
