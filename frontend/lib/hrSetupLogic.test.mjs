import test from "node:test";
import assert from "node:assert/strict";

import { INPUT_LIMITS } from "./inputLimits.mjs";
import {
  buildHrContextPayload,
  buildHrSetupFormFromApi,
  hasHrSetupValidationErrors,
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
        resumeText: "",
        profileText: "## Skills\n- SQL",
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
    "Extract a resume PDF profile or paste resume text.",
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

test("builds HR setup form from demo API fields", () => {
  assert.deepEqual(
    buildHrSetupFormFromApi({
      company_url: "",
      company_text: "# Company\nDemo company",
      role_description: "# Role\nDemo role",
      resume_text: "# Resume\nDemo resume",
      profile_text: "# Profile\nDemo profile",
    }),
    {
      companyUrl: "",
      companyText: "# Company\nDemo company",
      roleDescription: "# Role\nDemo role",
      roleUrl: "",
      resumeText: "# Resume\nDemo resume",
      profileText: "# Profile\nDemo profile",
    },
  );
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

test("builds HR context payload from extracted resume PDF profile", () => {
  assert.deepEqual(
    buildHrContextPayload(
      {
        ...validForm,
        resumeText: "",
        profileText: "## Skills\n- SQL",
      },
      { resumeInputMode: "resumePdf" },
    ),
    {
      mode: "llm",
      company_url: "https://example.com/about",
      role_description: "# Role\nAnalyze workforce data.",
      profile_text: "## Skills\n- SQL",
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
