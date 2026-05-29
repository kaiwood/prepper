export const INPUT_LIMITS = {
  chatMessage: 8000,
  currentQuestion: 8000,
  conversationHistoryContent: 8000,
  companyText: 40000,
  companyUrl: 2048,
  roleDescription: 40000,
  roleUrl: 2048,
  resumeText: 40000,
  profileText: 40000,
};

export function formatApiError(data, fallback = "Something went wrong.") {
  if (data?.error === "input_too_long") {
    const field = typeof data.field === "string" ? data.field : "input";
    const maxLength = Number.isFinite(data.max_length) ? data.max_length : null;
    return maxLength
      ? `${field} is too long. Maximum length is ${maxLength} characters.`
      : `${field} is too long.`;
  }

  return typeof data?.error === "string" ? data.error : fallback;
}

export function validateMaxLength(errors, field, label, value, maxLength) {
  if (typeof value === "string" && value.length > maxLength) {
    errors[field] = `${label} must be ${maxLength} characters or fewer.`;
  }
}
