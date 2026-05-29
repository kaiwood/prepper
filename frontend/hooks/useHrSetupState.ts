import { useState } from "react";
import {
  EMPTY_HR_SETUP_FORM,
  validateHrSetupForm,
} from "../lib/hrSetupLogic.mjs";
import type {
  HrCompanyInputMode,
  HrProfileInputMode,
  HrResumeInputMode,
  HrRoleInputMode,
  HrSetupFormState,
  HrSetupValidationErrors,
} from "../types/app";

type HrSetupValidationMessages = Parameters<typeof validateHrSetupForm>[1];

export function useHrSetupState(validationMessages: HrSetupValidationMessages) {
  const [hrSetupForm, setHrSetupForm] = useState<HrSetupFormState>({
    ...EMPTY_HR_SETUP_FORM,
  });
  const [hrCompanyInputMode, setHrCompanyInputMode] =
    useState<HrCompanyInputMode>("companyText");
  const [hrRoleInputMode, setHrRoleInputMode] =
    useState<HrRoleInputMode>("roleDescription");
  const [hrResumeInputMode, setHrResumeInputMode] =
    useState<HrResumeInputMode>("resumeText");
  const [hrProfileInputMode, setHrProfileInputMode] =
    useState<HrProfileInputMode>("profileText");
  const [hrSetupErrors, setHrSetupErrors] =
    useState<HrSetupValidationErrors>({});
  const [hrProfileUrl, setHrProfileUrl] = useState("");
  const [hrProfileOauthToken, setHrProfileOauthToken] = useState("");

  function revalidateIfNeeded(
    form: HrSetupFormState,
    modes: {
      companyInputMode?: HrCompanyInputMode;
      roleInputMode?: HrRoleInputMode;
      resumeInputMode?: HrResumeInputMode;
    } = {},
  ) {
    setHrSetupErrors((prev) => {
      if (Object.keys(prev).length === 0) {
        return prev;
      }
      return validateHrSetupForm(form, validationMessages, {
        companyInputMode: modes.companyInputMode ?? hrCompanyInputMode,
        roleInputMode: modes.roleInputMode ?? hrRoleInputMode,
        resumeInputMode: modes.resumeInputMode ?? hrResumeInputMode,
      });
    });
  }

  const updateHrCompanyInputMode = (mode: HrCompanyInputMode) => {
    setHrCompanyInputMode(mode);
    revalidateIfNeeded(hrSetupForm, { companyInputMode: mode });
  };

  const updateHrRoleInputMode = (mode: HrRoleInputMode) => {
    setHrRoleInputMode(mode);
    revalidateIfNeeded(hrSetupForm, { roleInputMode: mode });
  };

  const updateHrResumeInputMode = (mode: HrResumeInputMode) => {
    setHrResumeInputMode(mode);
    revalidateIfNeeded(hrSetupForm, { resumeInputMode: mode });
  };

  const updateHrProfileInputMode = (mode: HrProfileInputMode) => {
    setHrProfileInputMode(mode);
  };

  const updateHrSetupField = (
    field: keyof HrSetupFormState,
    value: string,
  ) => {
    const nextForm = { ...hrSetupForm, [field]: value };
    setHrSetupForm((prev) => ({ ...prev, [field]: value }));
    revalidateIfNeeded(nextForm);
  };

  function resetHrSetupState() {
    setHrSetupForm({ ...EMPTY_HR_SETUP_FORM });
    setHrCompanyInputMode("companyText");
    setHrRoleInputMode("roleDescription");
    setHrResumeInputMode("resumeText");
    setHrProfileInputMode("profileText");
    setHrSetupErrors({});
    setHrProfileUrl("");
    setHrProfileOauthToken("");
  }

  return {
    hrCompanyInputMode,
    hrProfileInputMode,
    hrProfileOauthToken,
    hrProfileUrl,
    hrResumeInputMode,
    hrRoleInputMode,
    hrSetupErrors,
    hrSetupForm,
    resetHrSetupState,
    setHrCompanyInputMode,
    setHrProfileOauthToken,
    setHrProfileUrl,
    setHrResumeInputMode,
    setHrRoleInputMode,
    setHrSetupErrors,
    setHrSetupForm,
    updateHrCompanyInputMode,
    updateHrProfileInputMode,
    updateHrResumeInputMode,
    updateHrRoleInputMode,
    updateHrSetupField,
  };
}
