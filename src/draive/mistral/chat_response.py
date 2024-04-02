from typing import cast

from mistralai.models.chat_completion import ChatCompletionResponse, ChatMessage

from draive.mistral.chat_tools import (
    _execute_chat_tool_calls,  # pyright: ignore[reportPrivateUsage]
)
from draive.mistral.client import MistralClient
from draive.mistral.config import MistralChatConfig
from draive.scope import (
    ArgumentsTrace,
    ResultTrace,
    TokenUsage,
    ctx,
)
from draive.tools import Toolbox, ToolException

__all__ = [
    "_chat_response",
]


async def _chat_response(
    *,
    client: MistralClient,
    config: MistralChatConfig,
    messages: list[ChatMessage],
    tools: Toolbox | None,
) -> str:
    with ctx.nested(
        "chat_response",
        metrics=[ArgumentsTrace(messages=messages.copy())],
    ):
        completion: ChatCompletionResponse = await client.chat_completion(
            config=config,
            messages=messages,
            tools=cast(
                list[dict[str, object]],
                tools.available_tools if tools else [],
            ),
        )

        if usage := completion.usage:
            ctx.record(
                TokenUsage(
                    input_tokens=usage.prompt_tokens,
                    output_tokens=usage.completion_tokens,
                ),
            )

        if not completion.choices:
            raise ToolException("Invalid Mistral completion - missing messages!", completion)

        completion_message: ChatMessage = completion.choices[0].message

        if (tool_calls := completion_message.tool_calls) and (tools := tools):
            messages.extend(
                await _execute_chat_tool_calls(
                    tool_calls=tool_calls,
                    tools=tools,
                )
            )
            ctx.record(ResultTrace(tool_calls))

        elif message := completion_message.content:
            ctx.record(ResultTrace(message))
            match message:
                case str() as content:
                    return content

                # API docs say that it can be only a string in response
                # however library model allows list as well
                case other:
                    return str(other)

        else:
            raise ToolException("Invalid Mistral completion", completion)

    # recursion outside of context
    return await _chat_response(
        client=client,
        config=config,
        messages=messages,
        tools=tools,
    )
