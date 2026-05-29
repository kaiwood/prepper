import test from "node:test";
import assert from "node:assert/strict";

import { INPUT_LIMITS } from "./inputLimits.mjs";
import {
  EMPTY_HR_SETUP_FORM,
  buildHrContextPayload,
  buildHrSetupFormFromApi,
  hasHrResolvedCompanyText,
  hasHrResolvedRoleDescription,
  hasHrSetupValidationErrors,
  mergeHrResolvedSetupFields,
  validateHrSetupForm,
} from "./hrSetupLogic.mjs";

const validForm = {
  companyUrl: "https://example.com/about",
  companyText: "",
  roleDescription: "# Role\nAnalyze workforce data.",
  roleUrl: "",
  resumeText: "# Resume\nSQL and customer analytics.",
  profileText: "Responsible AI interests.",
};

test("empty HR setup form has no prefilled data", () => {
  assert.deepEqual(EMPTY_HR_SETUP_FORM, {
    companyUrl: "",
    companyText: "",
    roleDescription: "",
    roleUrl: "",
    resumeText: "",
    profileText: "",
  });
});

test("validates required HR setup fields", () => {
  assert.deepEqual(validateHrSetupForm(validForm), {});
  assert.equal(hasHrSetupValidationErrors({}), false);

  const errors = validateHrSetupForm({
    companyUrl: "",
    companyText: "",
    roleDescription: "",
    roleUrl: "",
    resumeText: "",
    profileText: "",
  });

  assert.equal(hasHrSetupValidationErrors(errors), true);
  assert.equal(errors.company, "Enter a company URL or paste company text.");
  assert.equal(errors.roleDescription, "Enter either a role URL or role description.");
  assert.equal(errors.resumeText, "Resume text is required.");
});

test("validates HR setup max lengths", () => {
  const errors = validateHrSetupForm({
    ...validForm,
    companyUrl: "",
    companyText: "x".repeat(INPUT_LIMITS.companyText + 1),
    profileText: "x".repeat(INPUT_LIMITS.profileText + 1),
  });

  assert.equal(
    errors.company,
    `Company text must be ${INPUT_LIMITS.companyText} characters or fewer.`,
  );
  assert.equal(
    errors.profileText,
    `Profile text must be ${INPUT_LIMITS.profileText} characters or fewer.`,
  );
});

test("rejects company URL and text together", () => {
  assert.deepEqual(
    validateHrSetupForm({
      ...validForm,
      companyText: "# Company\nPrivacy-first analytics.",
    }),
    { company: "Enter either a company URL or company text, not both." },
  );
});

test("validates only the active company tab", () => {
  assert.deepEqual(
    validateHrSetupForm(
      {
        ...validForm,
        companyText: "# Company\nPrivacy-first analytics.",
      },
      undefined,
      { companyInputMode: "companyText" },
    ),
    {},
  );

  assert.equal(
    validateHrSetupForm(
      {
        ...validForm,
        companyText: "",
      },
      undefined,
      { companyInputMode: "companyText" },
    ).company,
    "Enter a company URL or paste company text.",
  );

  assert.deepEqual(
    validateHrSetupForm(
      {
        ...validForm,
        companyUrl: "https://example.com/" + "x".repeat(INPUT_LIMITS.companyUrl),
        companyText: "# Company\nPrivacy-first analytics.",
      },
      undefined,
      { companyInputMode: "companyText" },
    ),
    {},
  );
});

test("validates only the active resume tab", () => {
  assert.deepEqual(
    validateHrSetupForm(
      {
        ...validForm,
        resumeText: "# Resume\n- SQL",
        profileText: "",
      },
      undefined,
      { resumeInputMode: "resumePdf" },
    ),
    {},
  );

  assert.equal(
    validateHrSetupForm(
      {
        ...validForm,
        resumeText: "",
        profileText: "",
      },
      undefined,
      { resumeInputMode: "resumePdf" },
    ).resumeText,
    "Extract resume PDF text or paste resume text.",
  );
});

test("validates only the active role tab", () => {
  assert.deepEqual(
    validateHrSetupForm(
      {
        ...validForm,
        roleUrl: "https://example.com/jobs/analyst",
      },
      undefined,
      { roleInputMode: "roleDescription" },
    ),
    {},
  );

  assert.deepEqual(
    validateHrSetupForm(
      {
        ...validForm,
        roleDescription: "",
        roleUrl: "https://example.com/jobs/analyst",
      },
      undefined,
      { roleInputMode: "roleUrl" },
    ),
    {},
  );

  assert.equal(
    validateHrSetupForm(
      {
        ...validForm,
        roleDescription: "",
        roleUrl: "",
      },
      undefined,
      { roleInputMode: "roleUrl" },
    ).roleDescription,
    "Enter either a role URL or role description.",
  );
});


test("builds HR setup form from API fields", () => {
  assert.deepEqual(
    buildHrSetupFormFromApi({
      company_url: " https://example.com/about ",
      company_text: " ",
      role_description: " Role summary ",
      resume_text: " Resume summary ",
      profile_text: " Profile summary ",
    }),
    {
      companyUrl: "https://example.com/about",
      companyText: "",
      roleDescription: "Role summary",
      roleUrl: "",
      resumeText: "Resume summary",
      profileText: "Profile summary",
    },
  );
});

test("builds HR setup form from multiline API fields", () => {
  assert.deepEqual(
    buildHrSetupFormFromApi({
      company_url: "",
      company_text: "# Company\nExample company",
      role_description: "# Role\nExample role",
      resume_text: "# Resume\nExample resume",
      profile_text: "# Profile\nExample profile",
    }),
    {
      companyUrl: "",
      companyText: "# Company\nExample company",
      roleDescription: "# Role\nExample role",
      roleUrl: "",
      resumeText: "# Resume\nExample resume",
      profileText: "# Profile\nExample profile",
    },
  );
});

test("merges resolved setup fields into editable form fields", () => {
  const form = {
    ...validForm,
    companyText: "",
    roleDescription: "",
    roleUrl: "https://example.com/jobs/analyst",
  };
  const response = {
    resolved_setup: {
      company_text: " # Company\nFetched company ",
      role_description: " # Role\nFetched role ",
    },
  };

  assert.deepEqual(mergeHrResolvedSetupFields(form, response), {
    ...form,
    companyText: "# Company\nFetched company",
    roleDescription: "# Role\nFetched role",
  });
  assert.equal(hasHrResolvedCompanyText(response), true);
  assert.equal(hasHrResolvedRoleDescription(response), true);
});


test("builds HR context payload from company URL", () => {
  assert.deepEqual(buildHrContextPayload(validForm), {
    mode: "llm",
    company_url: "https://example.com/about",
    role_description: "# Role\nAnalyze workforce data.",
    resume_text: "# Resume\nSQL and customer analytics.",
    profile_text: "Responsible AI interests.",
  });
});

test("builds HR context payload from extracted resume PDF text", () => {
  assert.deepEqual(
    buildHrContextPayload(
      {
        ...validForm,
        resumeText: "# Resume\n- SQL",
        profileText: "",
      },
      { resumeInputMode: "resumePdf" },
    ),
    {
      mode: "llm",
      company_url: "https://example.com/about",
      role_description: "# Role\nAnalyze workforce data.",
      resume_text: "# Resume\n- SQL",
    },
  );
});

test("builds HR context payload from pasted company text", () => {
  assert.deepEqual(
    buildHrContextPayload(
      {
        companyUrl: " ",
        companyText: " # Company\nEvidence-led decisions. ",
        roleDescription: " Role summary ",
        roleUrl: " ",
        resumeText: " Resume summary ",
        profileText: " ",
      },
      { mode: "llm" },
    ),
    {
      mode: "llm",
      company_text: "# Company\nEvidence-led decisions.",
      role_description: "Role summary",
      resume_text: "Resume summary",
    },
  );
});

test("builds HR context payload from role URL", () => {
  assert.deepEqual(
    buildHrContextPayload({
      ...validForm,
      roleDescription: " ",
      roleUrl: " https://example.com/jobs/analyst ",
    }),
    {
      mode: "llm",
      company_url: "https://example.com/about",
      role_url: "https://example.com/jobs/analyst",
      resume_text: "# Resume\nSQL and customer analytics.",
      profile_text: "Responsible AI interests.",
    },
  );
});


test("builds HR context payload from the active role tab only", () => {
  const formWithBothRoleInputs = {
    ...validForm,
    roleUrl: " https://example.com/jobs/analyst ",
  };

  assert.deepEqual(
    buildHrContextPayload(formWithBothRoleInputs, {
      roleInputMode: "roleDescription",
    }),
    {
      mode: "llm",
      company_url: "https://example.com/about",
      role_description: "# Role\nAnalyze workforce data.",
      resume_text: "# Resume\nSQL and customer analytics.",
      profile_text: "Responsible AI interests.",
    },
  );

  assert.deepEqual(
    buildHrContextPayload(formWithBothRoleInputs, {
      roleInputMode: "roleUrl",
    }),
    {
      mode: "llm",
      company_url: "https://example.com/about",
      role_url: "https://example.com/jobs/analyst",
      resume_text: "# Resume\nSQL and customer analytics.",
      profile_text: "Responsible AI interests.",
    },
  );
});


test("builds HR context payload from the active company tab only", () => {
  const formWithBothCompanyInputs = {
    ...validForm,
    companyText: " # Company\nEvidence-led decisions. ",
  };

  assert.deepEqual(
    buildHrContextPayload(formWithBothCompanyInputs, {
      companyInputMode: "companyText",
    }),
    {
      mode: "llm",
      company_text: "# Company\nEvidence-led decisions.",
      role_description: "# Role\nAnalyze workforce data.",
      resume_text: "# Resume\nSQL and customer analytics.",
      profile_text: "Responsible AI interests.",
    },
  );

  assert.deepEqual(
    buildHrContextPayload(formWithBothCompanyInputs, {
      companyInputMode: "companyUrl",
    }),
    {
      mode: "llm",
      company_url: "https://example.com/about",
      role_description: "# Role\nAnalyze workforce data.",
      resume_text: "# Resume\nSQL and customer analytics.",
      profile_text: "Responsible AI interests.",
    },
  );
});
