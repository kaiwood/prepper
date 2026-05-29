import { INPUT_LIMITS } from "./inputLimits.mjs";

export const DEFAULT_HR_CONTEXT_MODE = "llm";

const DEFAULT_VALIDATION_MESSAGES = {
  companyEither: "Enter either a company URL or company text, not both.",
  companyRequired: "Enter a company URL or paste company text.",
  roleRequired: "Enter either a role URL or role description.",
  roleEither: "Enter either a role URL or role description, not both.",
  resumeRequired: "Resume text is required.",
  companyUrlLabel: "Company URL",
  companyTextLabel: "Company text",
  roleDescriptionLabel: "Role description",
  roleUrlLabel: "Role URL",
  resumeTextLabel: "Resume text",
  profileTextLabel: "Profile text",
  tooLong: (label, maxLength) =>
    `${label} must be ${maxLength} characters or fewer.`,
};

export function validateHrSetupForm(
  form,
  messages = DEFAULT_VALIDATION_MESSAGES,
  options = {},
) {
  const companyInputMode = normalizeCompanyInputMode(options.companyInputMode);
  const companyUrl = normalizeText(form?.companyUrl);
  const companyText = normalizeText(form?.companyText);
  const activeCompanyUrl = companyInputMode === "companyUrl" ? companyUrl : "";
  const activeCompanyText = companyInputMode === "companyText" ? companyText : "";
  const roleInputMode = normalizeRoleInputMode(options.roleInputMode);
  const roleDescription = normalizeText(form?.roleDescription);
  const roleUrl = normalizeText(form?.roleUrl);
  const activeRoleDescription = roleInputMode === "roleDescription" ? roleDescription : "";
  const activeRoleUrl = roleInputMode === "roleUrl" ? roleUrl : "";
  const resumeText = normalizeText(form?.resumeText);
  const errors = {};

  if (companyInputMode) {
    if (!activeCompanyUrl && !activeCompanyText) {
      errors.company = messages.companyRequired;
    }
  } else if (companyUrl && companyText) {
    errors.company = messages.companyEither;
  } else if (!companyUrl && !companyText) {
    errors.company = messages.companyRequired;
  }

  if (roleInputMode) {
    if (!activeRoleDescription && !activeRoleUrl) {
      errors.roleDescription = messages.roleRequired;
    }
  } else if (roleDescription && roleUrl) {
    errors.roleDescription = messages.roleEither ?? messages.roleRequired;
  } else if (!roleDescription && !roleUrl) {
    errors.roleDescription = messages.roleRequired;
  }

  if (!resumeText) {
    errors.resumeText = messages.resumeRequired;
  }

  validateHrMaxLength(
    errors,
    "company",
    messages.companyUrlLabel,
    companyInputMode ? activeCompanyUrl : companyUrl,
    INPUT_LIMITS.companyUrl,
    messages,
  );
  validateHrMaxLength(
    errors,
    "company",
    messages.companyTextLabel,
    companyInputMode ? activeCompanyText : companyText,
    INPUT_LIMITS.companyText,
    messages,
  );
  validateHrMaxLength(
    errors,
    "roleDescription",
    messages.roleDescriptionLabel,
    roleInputMode ? activeRoleDescription : roleDescription,
    INPUT_LIMITS.roleDescription,
    messages,
  );
  validateHrMaxLength(
    errors,
    "roleDescription",
    messages.roleUrlLabel,
    roleInputMode ? activeRoleUrl : roleUrl,
    INPUT_LIMITS.roleUrl,
    messages,
  );
  validateHrMaxLength(
    errors,
    "resumeText",
    messages.resumeTextLabel,
    resumeText,
    INPUT_LIMITS.resumeText,
    messages,
  );
  validateHrMaxLength(
    errors,
    "profileText",
    messages.profileTextLabel,
    normalizeText(form?.profileText),
    INPUT_LIMITS.profileText,
    messages,
  );

  return errors;
}

export function hasHrSetupValidationErrors(errors) {
  return Boolean(errors && Object.keys(errors).length > 0);
}

export function buildHrSetupFormFromApi(setup) {
  return {
    companyUrl: normalizeText(setup?.company_url),
    companyText: normalizeText(setup?.company_text),
    roleDescription: normalizeText(setup?.role_description),
    roleUrl: normalizeText(setup?.role_url),
    resumeText: normalizeText(setup?.resume_text),
    profileText: normalizeText(setup?.profile_text),
  };
}

export function buildHrContextPayload(form, options = {}) {
  const roleInputMode = normalizeRoleInputMode(options.roleInputMode);
  const roleDescription = normalizeText(form?.roleDescription);
  const roleUrl = normalizeText(form?.roleUrl);
  const payload = {
    mode: options.mode ?? DEFAULT_HR_CONTEXT_MODE,
    resume_text: normalizeText(form?.resumeText),
  };
  if ((!roleInputMode || roleInputMode === "roleUrl") && roleUrl) {
    payload.role_url = roleUrl;
  }

  if ((!roleInputMode || roleInputMode === "roleDescription") && roleDescription) {
    payload.role_description = roleDescription;
  }

  const companyInputMode = normalizeCompanyInputMode(options.companyInputMode);
  const companyUrl = normalizeText(form?.companyUrl);
  const companyText = normalizeText(form?.companyText);
  const profileText = normalizeText(form?.profileText);

  if ((!companyInputMode || companyInputMode === "companyUrl") && companyUrl) {
    payload.company_url = companyUrl;
  }

  if ((!companyInputMode || companyInputMode === "companyText") && companyText) {
    payload.company_text = companyText;
  }

  if (profileText) {
    payload.profile_text = profileText;
  }

  return payload;
}

function validateHrMaxLength(errors, field, label, value, maxLength, messages) {
  if (typeof value === "string" && value.length > maxLength) {
    errors[field] = messages.tooLong(label, maxLength);
  }
}

function normalizeCompanyInputMode(value) {
  return value === "companyText" || value === "companyUrl" ? value : null;
}

function normalizeRoleInputMode(value) {
  return value === "roleDescription" || value === "roleUrl" ? value : null;
}

function normalizeText(value) {
  return typeof value === "string" ? value.trim() : "";
}
