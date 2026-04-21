---
description: "Use when writing or editing Next.js pages, components, or API routes in the frontend/ directory. Covers TypeScript conventions, Tailwind styling, app router patterns, and backend communication."
applyTo: "frontend/**"
---

# Frontend Conventions (Next.js + TypeScript + Tailwind)

## Before Writing Any Next.js Code

Read the relevant guide in `node_modules/next/dist/docs/` before using any Next.js API.
This version may have breaking changes from your training data — heed deprecation notices.

## TypeScript

- Use TypeScript everywhere; no `any`.
- Prefer explicit return types on exported functions/components.

## Components & Routing

- Use the **App Router** (`app/` directory).
- Add `"use client"` at the top of any component that uses `useState`, `useEffect`, or other client-only hooks.
- Server components are the default — keep them server-side unless you need client interactivity.

## Styling

- Use **Tailwind CSS** utility classes exclusively.
- Do not add CSS-in-JS libraries or extra CSS modules for new code.

## Calling the Backend

- Always use the `NEXT_PUBLIC_API_URL` environment variable as the base URL:
  ```ts
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, { ... });
  ```
- Include the current conversation history in every request:
  ```ts
  body: JSON.stringify({ message: prompt, conversation_history: history });
  ```
  where `history` is a snapshot of prior `{role, content}` turns taken **before** appending the new user message.
- Model state as:
  ```ts
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  ```
  `ConversationMessage` is `{ role: "user" | "assistant"; content: string }`.
- On success, append the assistant reply to `conversation`; do **not** store a separate `reply` state.
- On non-OK responses, read `data.error` (the backend always returns `{"error": "..."}` on failure).
- Wrap fetch in try/catch; set `error` on network failure.

## Forms

- Use a `<form onSubmit={handler}>` pattern.
- Guard against empty/whitespace-only input **and** `loading === true` before submitting.
- Disable or show a loading indicator while the request is in-flight.
- When the user submits, optimistically append the user message to `conversation` and clear the input field immediately; append the assistant reply on success.
- Provide a "Clear conversation" button that resets `conversation` to `[]`; disable it while `loading` or when `conversation` is empty.

## Chat Thread UI

- Render the conversation as a scrollable thread above the form.
- User messages: right-aligned, blue background (`bg-blue-600 text-white`).
- Assistant messages: left-aligned, light gray background (`bg-gray-100 text-gray-900`).
- Show a "Thinking..." placeholder bubble (assistant style) while `loading` is true.
- Show an empty-state hint when `conversation` is empty.
