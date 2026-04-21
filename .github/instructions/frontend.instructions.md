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
- Model error/loading/reply state with three separate pieces of state:
  ```ts
  const [reply, setReply] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  ```
- On non-OK responses, read `data.error` (the backend always returns `{"error": "..."}` on failure).
- Wrap fetch in try/catch; set `error` on network failure.

## Forms

- Use a `<form onSubmit={handler}>` pattern.
- Guard against empty/whitespace-only input before submitting.
- Disable or show a loading indicator while the request is in-flight.
