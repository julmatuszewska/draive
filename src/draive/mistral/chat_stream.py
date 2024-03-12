from collections.abc import AsyncIterable, AsyncIterator
from typing import Protocol, Self, cast

from mistralai.models.chat_completion import (
    ChatCompletionStreamResponse,
    ChatMessage,
    DeltaMessage,
    ToolCall,
)

from draive.mistral.chat_tools import (
    MistralChatStreamingToolStatus,
    _execute_chat_tool_calls,  # pyright: ignore[reportPrivateUsage]
    _flush_chat_tool_calls,  # pyright: ignore[reportPrivateUsage]
)
from draive.mistral.client import MistralClient
from draive.mistral.config import MistralChatConfig
from draive.scope import ArgumentsTrace, ResultTrace, ctx
from draive.tools import ToolException
from draive.types import Model, StreamingProgressUpdate, Toolset

__all__ = [
    "MistralChatStream",
    "MistralChatStreamingMessagePart",
    "MistralChatStreamingPart",
    "_chat_stream",
]


class MistralChatStreamingMessagePart(Model):
    content: str


MistralChatStreamingPart = MistralChatStreamingToolStatus | MistralChatStreamingMessagePart


class MistralChatStream(Protocol):
    def as_json(self) -> AsyncIterator[str]:
        ...

    def __aiter__(self) -> Self:
        ...

    async def __anext__(self) -> MistralChatStreamingPart:
        ...


async def _chat_stream(
    *,
    client: MistralClient,
    config: MistralChatConfig,
    messages: list[ChatMessage],
    toolset: Toolset | None,
    progress: StreamingProgressUpdate[MistralChatStreamingPart],
) -> str:
    async with ctx.nested(
        "chat_stream",
        ArgumentsTrace(messages=messages.copy()),
    ):
        completion_stream: AsyncIterable[
            ChatCompletionStreamResponse
        ] = await client.chat_completion(
            config=config,
            messages=messages,
            tools=cast(
                list[dict[str, object]],
                toolset.available_tools if toolset else [],
            ),
            stream=True,
        )
        completion_stream_iterator: AsyncIterator[
            ChatCompletionStreamResponse
        ] = completion_stream.__aiter__()

        while True:  # load chunks to decide what to do next
            head: ChatCompletionStreamResponse
            try:
                head = await anext(completion_stream_iterator)
            except StopAsyncIteration as exc:
                # could not decide what to do before stream end
                raise ToolException("Invalid Mistral completion stream") from exc

            if not head.choices:
                raise ToolException("Invalid Mistral completion - missing deltas!", head)

            completion_head: DeltaMessage = head.choices[0].delta

            # TODO: record token usage

            if completion_head.tool_calls is not None and (toolset := toolset):
                tool_calls: list[ToolCall] = await _flush_chat_tool_calls(
                    tool_calls=completion_head.tool_calls,
                    completion_stream=completion_stream_iterator,
                )
                messages.extend(
                    await _execute_chat_tool_calls(
                        tool_calls=tool_calls,
                        toolset=toolset,
                        progress=progress,
                    )
                )
                await ctx.record(ResultTrace(tool_calls))
                break  # after processing tool calls continue with recursion in outer context

            elif completion_head.content is not None:
                result: str = completion_head.content
                if result:  # provide head / first part if not empty
                    progress(update=MistralChatStreamingMessagePart(content=result))

                async for part in completion_stream:
                    # we are always requesting single result - no need to take care of indices
                    part_text: str = part.choices[0].delta.content or ""
                    if not part_text:
                        continue  # skip empty parts
                    progress(update=MistralChatStreamingMessagePart(content=part_text))
                    result += part_text

                await ctx.record(ResultTrace(result))
                return result  # we hav final result here

            else:
                continue  # iterate over the stream until can decide what to do or reach the end

    # recursion outside of context
    return await _chat_stream(
        client=client,
        config=config,
        messages=messages,
        toolset=toolset,
        progress=progress,
    )