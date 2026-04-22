from .client import get_client
from .conversation import Conversation


def get_chat_reply(
    message: str,
    conversation: Conversation | None = None,
    history_limit: int = 10,
    system_prompt: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    max_tokens: int | None = None,
) -> str:
    prompt = message.strip()
    if not prompt:
        raise ValueError("message is required")

    messages = [{"role": "user", "content": prompt}]
    if conversation is not None and history_limit > 1:
        context_messages = conversation.get_recent_messages(limit=history_limit - 1)
        messages = context_messages + messages

    normalized_system_prompt = (system_prompt or "").strip()
    if normalized_system_prompt:
        messages = [
            {"role": "system", "content": normalized_system_prompt},
            *messages,
        ]

    client, model = get_client()

    kwargs: dict = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if top_p is not None:
        kwargs["top_p"] = top_p
    if frequency_penalty is not None:
        kwargs["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        kwargs["presence_penalty"] = presence_penalty
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    response = client.chat.completions.create(**kwargs)

    reply = response.choices[0].message.content
    normalized_reply = (reply or "").strip()

    if conversation is not None:
        conversation.add_user_message(prompt)
        conversation.add_assistant_reply(normalized_reply)

    return normalized_reply
