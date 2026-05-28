import { INPUT_LIMITS, validateMaxLength } from "./inputLimits.mjs";

export const DEFAULT_HR_CONTEXT_MODE = "llm";

export function validateHrSetupForm(form) {
  const companyUrl = normalizeText(form?.companyUrl);
  const companyText = normalizeText(form?.companyText);
  const roleDescription = normalizeText(form?.roleDescription);
  const resumeText = normalizeText(form?.resumeText);
  const errors = {};

  if (companyUrl && companyText) {
    errors.company = "Enter either a company URL or company text, not both.";
  } else if (!companyUrl && !companyText) {
    errors.company = "Enter a company URL or paste company text.";
  }

  if (!roleDescription) {
    errors.roleDescription = "Role description is required.";
  }

  if (!resumeText) {
    errors.resumeText = "Resume text is required.";
  }

  validateMaxLength(
    errors,
    "company",
    "Company URL",
    companyUrl,
    INPUT_LIMITS.companyUrl,
  );
  validateMaxLength(
    errors,
    "company",
    "Company text",
    companyText,
    INPUT_LIMITS.companyText,
  );
  validateMaxLength(
    errors,
    "roleDescription",
    "Role description",
    roleDescription,
    INPUT_LIMITS.roleDescription,
  );
  validateMaxLength(
    errors,
    "resumeText",
    "Resume text",
    resumeText,
    INPUT_LIMITS.resumeText,
  );
  validateMaxLength(
    errors,
    "profileText",
    "Profile text",
    normalizeText(form?.profileText),
    INPUT_LIMITS.profileText,
  );

  return errors;
}

export function hasHrSetupValidationErrors(errors) {
  return Boolean(errors && Object.keys(errors).length > 0);
}

export function buildHrContextPayload(form, options = {}) {
  const payload = {
    mode: options.mode ?? DEFAULT_HR_CONTEXT_MODE,
    role_description: normalizeText(form?.roleDescription),
    resume_text: normalizeText(form?.resumeText),
  };

  const companyUrl = normalizeText(form?.companyUrl);
  const companyText = normalizeText(form?.companyText);
  const profileText = normalizeText(form?.profileText);

  if (companyUrl) {
    payload.company_url = companyUrl;
  }

  if (companyText) {
    payload.company_text = companyText;
  }

  if (profileText) {
    payload.profile_text = profileText;
  }

  return payload;
}

function normalizeText(value) {
  return typeof value === "string" ? value.trim() : "";
}
