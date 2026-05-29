import { INPUT_LIMITS } from "../../lib/inputLimits.mjs";
import type { HrWorkflowState } from "../../hooks/useHrWorkflow";
import HrInterviewPanel from "./HrInterviewPanel";

type HrSetupPanelProps = {
  state: HrWorkflowState;
};

export default function HrSetupPanel({ state }: HrSetupPanelProps) {
  return (
    <section className="w-full max-w-3xl rounded-xl border border-gray-200 bg-white p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold">Admin HR setup</h1>
          <p className="text-gray-500">
            Build a candidate evaluation context from company, role, resume,
            and optional profile information.
          </p>
        </div>
        <button
          type="button"
          onClick={state.handleLoadHrDemoSetup}
          disabled={state.hrContextLoading || state.hrDemoSetupLoading}
          className="rounded-lg border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-50 disabled:border-gray-200 disabled:text-gray-400"
        >
          {state.hrDemoSetupLoading ? "Loading demo..." : "Load demo data"}
        </button>
      </div>

      <form className="mt-6 flex flex-col gap-5" onSubmit={state.handleBuildHrContext}>
        <section className="flex flex-col gap-2">
          <label
            htmlFor="hr-company-url"
            className="text-sm font-medium text-gray-700"
          >
            Company URL
          </label>
          <input
            id="hr-company-url"
            type="url"
            value={state.hrSetupForm.companyUrl}
            onChange={(event) =>
              state.updateHrSetupField("companyUrl", event.target.value)
            }
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.companyUrl}
            placeholder="https://example.com/about"
            className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
          />
          <p className="text-sm text-gray-500">
            Use either a public company URL or paste company text below.
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <label
            htmlFor="hr-company-text"
            className="text-sm font-medium text-gray-700"
          >
            Company text
          </label>
          <textarea
            id="hr-company-text"
            value={state.hrSetupForm.companyText}
            onChange={(event) =>
              state.updateHrSetupField("companyText", event.target.value)
            }
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.companyText}
            rows={5}
            placeholder="Paste company overview, values, and interview-relevant facts."
            className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
          />
          {state.hrSetupErrors.company && (
            <p className="text-sm text-red-600">{state.hrSetupErrors.company}</p>
          )}
        </section>

        <section className="flex flex-col gap-2">
          <label
            htmlFor="hr-role-description"
            className="text-sm font-medium text-gray-700"
          >
            Role description
          </label>
          <textarea
            id="hr-role-description"
            value={state.hrSetupForm.roleDescription}
            onChange={(event) =>
              state.updateHrSetupField("roleDescription", event.target.value)
            }
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.roleDescription}
            rows={6}
            placeholder="Paste responsibilities, required skills, and success signals."
            className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
          />
          {state.hrSetupErrors.roleDescription && (
            <p className="text-sm text-red-600">
              {state.hrSetupErrors.roleDescription}
            </p>
          )}
        </section>

        <section className="flex flex-col gap-2">
          <label
            htmlFor="hr-resume-text"
            className="text-sm font-medium text-gray-700"
          >
            Resume text
          </label>
          <textarea
            id="hr-resume-text"
            value={state.hrSetupForm.resumeText}
            onChange={(event) =>
              state.updateHrSetupField("resumeText", event.target.value)
            }
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.resumeText}
            rows={6}
            placeholder="Paste candidate resume content."
            className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
          />
          {state.hrSetupErrors.resumeText && (
            <p className="text-sm text-red-600">
              {state.hrSetupErrors.resumeText}
            </p>
          )}
        </section>

        <section className="flex flex-col gap-2">
          <label
            htmlFor="hr-profile-text"
            className="text-sm font-medium text-gray-700"
          >
            Profile text optional
          </label>
          <textarea
            id="hr-profile-text"
            value={state.hrSetupForm.profileText}
            onChange={(event) =>
              state.updateHrSetupField("profileText", event.target.value)
            }
            disabled={state.hrContextLoading}
            maxLength={INPUT_LIMITS.profileText}
            rows={4}
            placeholder="Paste public profile or LinkedIn summary notes."
            className="border rounded-lg px-3 py-2 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
          />
          {state.hrSetupErrors.profileText && (
            <p className="text-sm text-red-600">
              {state.hrSetupErrors.profileText}
            </p>
          )}
        </section>

        <button
          type="submit"
          disabled={state.hrContextLoading}
          className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:bg-blue-300"
        >
          {state.hrContextLoading ? "Building context..." : "Build context"}
        </button>
      </form>

      {state.hrContextError && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {state.hrContextError}
        </div>
      )}

      {state.hrContextResult && (
        <section className="mt-6 flex flex-col gap-4 rounded-xl border border-gray-200 bg-gray-50 p-4">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold">Context summary</h2>
            <p className="text-sm text-gray-600">
              Status: <span className="font-medium">{state.hrContextResult.status}</span>
            </p>
            {state.hrContextId ? (
              <p className="text-sm text-gray-600">
                Context ID: <span className="font-mono">{state.hrContextId}</span>
              </p>
            ) : (
              <p className="text-sm text-amber-700">
                No context ID was returned. Review tool errors before continuing.
              </p>
            )}
          </div>

          {state.hrContextResult.summaries && (
            <div className="grid gap-3">
              {([
                ["Company", state.hrContextResult.summaries.company],
                ["Role", state.hrContextResult.summaries.role],
                ["Candidate", state.hrContextResult.summaries.candidate],
              ] as const).map(([label, value]) =>
                value ? (
                  <article
                    key={label}
                    className="rounded-lg border border-gray-200 bg-white p-3"
                  >
                    <h3 className="font-medium text-gray-900">{label}</h3>
                    <p className="mt-1 text-sm text-gray-700">{value}</p>
                  </article>
                ) : null,
              )}
            </div>
          )}

          {(state.hrContextResult.sources?.length ?? 0) > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">Sources</h3>
              <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                {state.hrContextResult.sources?.map((source, index) => (
                  <li key={`${source.id ?? source.uri ?? "source"}-${index}`}>
                    {source.title ?? source.id ?? "Source"}
                    {source.uri ? ` — ${source.uri}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(state.hrContextResult.tool_results?.length ?? 0) > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">Tool results</h3>
              <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                {state.hrContextResult.tool_results?.map((tool, index) => (
                  <li key={`${tool.tool_name ?? "tool"}-${index}`}>
                    {tool.tool_name ?? "tool"}: {tool.status ?? "unknown"}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(state.hrContextResult.tool_call_events?.length ?? 0) > 0 && (
            <div>
              <h3 className="font-medium text-gray-900">Tool-call events</h3>
              <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                {state.hrContextResult.tool_call_events?.map((event, index) => (
                  <li key={`${event.event_id ?? "event"}-${index}`}>
                    #{event.sequence ?? index + 1} {event.tool_name ?? "tool"}: {event.status ?? "unknown"}
                    {typeof event.duration_ms === "number" ? ` (${event.duration_ms}ms)` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(state.hrContextResult.errors?.length ?? 0) > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <h3 className="font-medium">Context build warnings</h3>
              <ul className="mt-1 list-disc list-inside">
                {state.hrContextResult.errors?.map((item, index) => (
                  <li key={`${item.tool_name ?? "error"}-${index}`}>
                    {item.tool_name ? `${item.tool_name}: ` : ""}
                    {item.message ?? "Unknown error"}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <HrInterviewPanel state={state} />
    </section>
  );
}
