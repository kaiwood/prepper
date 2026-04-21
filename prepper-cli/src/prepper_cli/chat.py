from .client import get_client


def get_chat_reply(message: str) -> str:
    prompt = message.strip()
    if not prompt:
        raise ValueError("message is required")

    client, model = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    reply = response.choices[0].message.content
    return (reply or "").strip()
