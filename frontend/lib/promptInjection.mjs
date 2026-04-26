const SUSPICIOUS_PROMPT_PATTERNS = [
  /ignore (all |any |the )?(previous|prior|above) instructions/i,
  /disregard (all |any |the )?(previous|prior|above) instructions/i,
  /system prompt/i,
  /developer message/i,
  /reveal (the )?(system|developer|hidden) instructions/i,
  /jailbreak/i,
  /prompt injection/i,
];

export function hasSuspiciousPromptInjectionPattern(input) {
  const normalized = input.trim();
  if (!normalized) {
    return false;
  }

  return SUSPICIOUS_PROMPT_PATTERNS.some((pattern) => pattern.test(normalized));
}

export { SUSPICIOUS_PROMPT_PATTERNS };
