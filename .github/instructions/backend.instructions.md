---
description: "Use when writing or editing Flask routes, blueprints, or app configuration in the backend/ directory. Covers app factory pattern, CORS setup, response format, and error handling."
applyTo: "backend/**"
---

# Backend Conventions (Flask)

## App Structure

- Use the **app factory** pattern: `create_app()` in `backend/app/__init__.py`.
- Register each feature area as a **Blueprint** in `backend/app/routes/`.
- Load environment variables via `load_dotenv()` at the top of the factory, before any config is read.

## CORS

- Apply `flask-cors` at the app level in `create_app()`.
- Restrict `origins` to `["http://localhost:3000", "http://127.0.0.1:3000"]` — do not open to `*` without explicit agreement.
- Allowed methods: `GET`, `POST`, `OPTIONS`.
- Allowed headers: `Content-Type`, `Authorization`.
- Add an explicit `OPTIONS` route handler for any endpoint that browsers will preflight.

## Response Format

| Outcome          | Status | Body                                              |
| ---------------- | ------ | ------------------------------------------------- |
| Success          | 200    | `jsonify({"reply": <value>})`                     |
| Client error     | 400    | `jsonify({"error": "<message>"})`                 |
| Bad LLM response | 502    | `jsonify({"error": "LLM request failed: <exc>"})` |

Always use `jsonify()`; never return raw dicts or strings.

## LLM Integration

- Import `get_chat_reply` and `Conversation` from the `prepper_cli` package — do not call OpenRouter directly from the backend.
  ```python
  from prepper_cli import Conversation, get_chat_reply
  ```
- Catch `ValueError` (bad input) → 400. Catch generic `Exception` (LLM failure) → 502.
- When `conversation_history` is present in the request body, validate it is a list, then call `Conversation.from_messages(conversation_history)` and pass the result to `get_chat_reply(message, conversation=conversation)`.
- The backend is **stateless** — no server-side session store. The client is responsible for maintaining and sending conversation history on each request.

## Environment Variables

- Read `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL` via `os.environ` or `os.getenv`.
- Never hard-code keys or URLs.

## Input Validation

- Validate and strip user input before passing it anywhere:
  ```python
  message = data.get("message", "").strip()
  if not message:
      return jsonify({"error": "message is required"}), 400
  ```
- When `conversation_history` is supplied, validate its shape before constructing a `Conversation`:
  ```python
  if not isinstance(conversation_history, list):
      return jsonify({"error": "conversation_history must be a list"}), 400
  try:
      conversation = Conversation.from_messages(conversation_history)
  except ValueError as exc:
      return jsonify({"error": str(exc)}), 400
  ```
