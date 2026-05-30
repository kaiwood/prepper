"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchMetrics } from "../lib/metricsApi";
import type {
  MetricsRecentEvent,
  MetricsResponse,
  MetricsToolSummary,
  TranslationStrings,
} from "../types/app";

const REFRESH_MS = 30_000;
const TOOL_COLORS = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2"];

type DashboardTranslations = TranslationStrings["dashboard"];

type DashboardPanelProps = {
  apiBaseUrl: string;
  ui: TranslationStrings;
};

export default function DashboardPanel({ apiBaseUrl, ui }: DashboardPanelProps) {
  const dashboard = ui.dashboard;
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedErrorEvent, setSelectedErrorEvent] =
    useState<MetricsRecentEvent | null>(null);

  const loadMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { ok, data } = await fetchMetrics(apiBaseUrl, {
        windowHours: 24,
        recentLimit: 30,
      });
      if (!ok) {
        setError(data.error ?? dashboard.metricsUnavailable);
        return;
      }
      setMetrics(data);
    } catch {
      setError(ui.errorBackendUnavailable);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, dashboard.metricsUnavailable, ui.errorBackendUnavailable]);

  useEffect(() => {
    const initialTimer = window.setTimeout(() => {
      void loadMetrics();
    }, 0);
    const refreshTimer = window.setInterval(() => {
      void loadMetrics();
    }, REFRESH_MS);
    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(refreshTimer);
    };
  }, [loadMetrics]);

  const overview = metrics?.overview ?? {};
  const rag = metrics?.rag ?? {};
  const llm = metrics?.llm ?? {};
  const safety = metrics?.safety ?? {};
  const timeBuckets = useMemo(
    () =>
      (metrics?.time_buckets ?? []).map((bucket) => ({
        ...bucket,
        label: formatHour(bucket.bucket),
      })),
    [metrics?.time_buckets],
  );
  const tools = metrics?.tools ?? [];
  const recentEvents = metrics?.recent_events ?? [];
  const health = resolveHealth(
    overview.error_rate ?? 0,
    overview.rate_limit_hits ?? 0,
    dashboard,
  );

  return (
    <section className="w-full max-w-6xl rounded-3xl border border-slate-200 bg-slate-950 p-1 shadow-xl">
      <div className="rounded-[1.35rem] bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 p-6 text-white">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.35em] text-blue-200">{dashboard.eyebrow}</p>
            <h1 className="mt-2 text-3xl font-bold md:text-4xl">{dashboard.title}</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">
              {dashboard.description}
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 rounded-2xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur md:items-end">
            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${health.className}`}>
              {health.label}
            </span>
            <span className="text-xs text-slate-300">
              {dashboard.updated} {formatDateTime(metrics?.generated_at, dashboard)}
            </span>
            <button
              type="button"
              onClick={() => void loadMetrics()}
              disabled={loading}
              className="rounded-lg border border-white/20 px-3 py-1 text-sm text-white transition hover:bg-white/10 disabled:opacity-50"
            >
              {loading ? dashboard.refreshing : dashboard.refresh}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-5 rounded-xl border border-red-300/40 bg-red-500/15 p-3 text-sm text-red-100">
            {error}
          </div>
        )}

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label={dashboard.requests} value={formatNumber(overview.requests_total)} hint={dashboard.last24Hours} accent="blue" />
          <MetricCard label={dashboard.errorRate} value={formatPercent(overview.error_rate)} hint={`${formatNumber(overview.error_count)} ${dashboard.errors}`} accent="red" />
          <MetricCard label={dashboard.p95Latency} value={`${formatNumber(overview.p95_latency_ms)}ms`} hint={`${dashboard.avgMs} ${formatNumber(overview.avg_latency_ms)}ms`} accent="amber" />
          <MetricCard label={dashboard.toolSuccess} value={formatPercent(overview.tool_success_rate)} hint={dashboard.allHrTools} accent="green" />
          <MetricCard label={dashboard.contextsBuilt} value={formatNumber(overview.hr_contexts_built)} hint={dashboard.hrSetupRuns} accent="blue" />
          <MetricCard label={dashboard.interviews} value={formatNumber(overview.interviews_started)} hint={`${formatNumber(overview.interviews_completed)} ${dashboard.completed}`} accent="violet" />
          <MetricCard label={dashboard.ragRetrievals} value={formatNumber(overview.rag_retrievals)} hint={`${formatPercent(rag.success_rate)} ${dashboard.success}`} accent="cyan" />
          <MetricCard label={dashboard.llmFailures} value={formatNumber(overview.llm_failures)} hint={`${formatNumber(llm.calls)} ${dashboard.totalCalls}`} accent="red" />
        </div>
      </div>

      <div className="grid gap-4 bg-slate-100 p-4 lg:grid-cols-2">
        <DashboardCard title={dashboard.trafficTitle} subtitle={dashboard.trafficSubtitle}>
          <ChartFrame>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeBuckets}>
                <defs>
                  <linearGradient id="requests" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="requests" name={dashboard.requests} stroke="#2563eb" fill="url(#requests)" />
                <Line type="monotone" dataKey="errors" name={dashboard.errors} stroke="#dc2626" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </ChartFrame>
        </DashboardCard>

        <DashboardCard title={dashboard.latencyTitle} subtitle={dashboard.latencySubtitle}>
          <ChartFrame>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeBuckets}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="avg_latency_ms" name={`${dashboard.avgMs} ms`} stroke="#f59e0b" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </DashboardCard>

        <DashboardCard title={dashboard.toolCallsTitle} subtitle={dashboard.toolCallsSubtitle}>
          <div className="grid gap-4 md:grid-cols-[220px_1fr]">
            <ChartFrame compact>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={tools} dataKey="calls" nameKey="name" innerRadius={46} outerRadius={78} paddingAngle={3}>
                    {tools.map((tool, index) => (
                      <Cell key={tool.name} fill={TOOL_COLORS[index % TOOL_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </ChartFrame>
            <div className="overflow-hidden rounded-xl border border-slate-200">
              <ToolTable tools={tools} dashboard={dashboard} />
            </div>
          </div>
        </DashboardCard>

        <DashboardCard title={dashboard.ragTitle} subtitle={dashboard.ragSubtitle}>
          <div className="grid gap-3 sm:grid-cols-2">
            <MiniStat label={dashboard.successRate} value={formatPercent(rag.success_rate)} />
            <MiniStat label={dashboard.avgTopRelevance} value={`${formatNumber(rag.avg_top_relevance_percent)}%`} />
            <MiniStat label={dashboard.avgChunks} value={formatNumber(rag.avg_chunk_count)} />
            <MiniStat label={dashboard.noResultRetrievals} value={formatNumber(rag.no_result_count)} />
            <MiniStat label={dashboard.avgDuration} value={`${formatNumber(rag.avg_duration_ms)}ms`} />
            <MiniStat label={dashboard.embeddingFailures} value={formatNumber(rag.embedding_failures)} />
          </div>
        </DashboardCard>

        <DashboardCard title={dashboard.llmTitle} subtitle={dashboard.llmSubtitle}>
          <ChartFrame compact>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={llm.operations ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="operation" tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="calls" name={dashboard.calls} fill="#2563eb" />
                <Bar dataKey="errors" name={dashboard.errors} fill="#dc2626" />
              </BarChart>
            </ResponsiveContainer>
          </ChartFrame>
        </DashboardCard>

        <DashboardCard title={dashboard.safetyTitle} subtitle={dashboard.safetySubtitle}>
          <div className="grid gap-3 sm:grid-cols-2">
            <MiniStat label={dashboard.rateLimitHits} value={formatNumber(safety.rate_limit_hits)} tone="amber" />
            <MiniStat label={dashboard.blockedUrls} value={formatNumber(safety.blocked_url_attempts)} tone="red" />
            <MiniStat label={dashboard.oversizedInputs} value={formatNumber(safety.oversized_input_rejections)} tone="red" />
            <MiniStat label={dashboard.invalidPdfs} value={formatNumber(safety.invalid_pdf_uploads)} tone="amber" />
            <MiniStat label={dashboard.validationErrors} value={formatNumber(safety.client_validation_errors)} tone="amber" />
            <MiniStat label={dashboard.debugRequests} value={formatNumber(safety.debug_context_requests)} tone="blue" />
          </div>
        </DashboardCard>
      </div>

      <div className="rounded-b-[1.35rem] bg-slate-100 px-4 pb-4">
        <DashboardCard title={dashboard.recentActivityTitle} subtitle={dashboard.recentActivitySubtitle}>
          <EventTimeline
            events={recentEvents}
            dashboard={dashboard}
            onSelectError={setSelectedErrorEvent}
          />
        </DashboardCard>
      </div>

      {selectedErrorEvent && (
        <ErrorDetailsOverlay
          event={selectedErrorEvent}
          dashboard={dashboard}
          onClose={() => setSelectedErrorEvent(null)}
        />
      )}
    </section>
  );
}

function MetricCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint: string;
  accent: "blue" | "green" | "red" | "amber" | "violet" | "cyan";
}) {
  const accentClasses = {
    blue: "from-blue-500/25 to-blue-500/5 text-blue-100",
    green: "from-green-500/25 to-green-500/5 text-green-100",
    red: "from-red-500/25 to-red-500/5 text-red-100",
    amber: "from-amber-500/25 to-amber-500/5 text-amber-100",
    violet: "from-violet-500/25 to-violet-500/5 text-violet-100",
    cyan: "from-cyan-500/25 to-cyan-500/5 text-cyan-100",
  }[accent];
  return (
    <article className={`rounded-2xl border border-white/10 bg-gradient-to-br p-4 ${accentClasses}`}>
      <p className="text-xs uppercase tracking-wide text-slate-300">{label}</p>
      <p className="mt-2 text-3xl font-bold text-white">{value}</p>
      <p className="mt-1 text-sm text-slate-300">{hint}</p>
    </article>
  );
}

function DashboardCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="text-sm text-slate-500">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

function ChartFrame({ children, compact = false }: { children: React.ReactNode; compact?: boolean }) {
  return <div className={compact ? "h-56" : "h-72"}>{children}</div>;
}

function MiniStat({
  label,
  value,
  tone = "blue",
}: {
  label: string;
  value: string;
  tone?: "blue" | "amber" | "red";
}) {
  const dotClass = {
    blue: "bg-blue-500",
    amber: "bg-amber-500",
    red: "bg-red-500",
  }[tone];
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <span className={`h-2 w-2 rounded-full ${dotClass}`} />
        {label}
      </div>
      <p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function ToolTable({
  tools,
  dashboard,
}: {
  tools: MetricsToolSummary[];
  dashboard: DashboardTranslations;
}) {
  if (tools.length === 0) {
    return <p className="p-4 text-sm text-slate-500">{dashboard.noToolCalls}</p>;
  }
  return (
    <table className="w-full text-left text-sm">
      <thead className="bg-slate-50 text-xs uppercase text-slate-500">
        <tr>
          <th className="px-3 py-2">{dashboard.tool}</th>
          <th className="px-3 py-2">{dashboard.calls}</th>
          <th className="px-3 py-2">{dashboard.errors}</th>
          <th className="px-3 py-2">{dashboard.avg}</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {tools.map((tool) => (
          <tr key={tool.name}>
            <td className="px-3 py-2 font-medium text-slate-800">{tool.name}</td>
            <td className="px-3 py-2">{tool.calls}</td>
            <td className="px-3 py-2 text-red-600">{tool.errors}</td>
            <td className="px-3 py-2">{tool.avg_duration_ms}ms</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function EventTimeline({
  events,
  dashboard,
  onSelectError,
}: {
  events: MetricsRecentEvent[];
  dashboard: DashboardTranslations;
  onSelectError: (event: MetricsRecentEvent) => void;
}) {
  if (events.length === 0) {
    return <p className="text-sm text-slate-500">{dashboard.noOperationalEvents}</p>;
  }
  return (
    <ol className="relative border-l border-slate-200 pl-5">
      {events.map((event, index) => {
        const hasErrorDetails = isErrorEvent(event);
        const CardElement = hasErrorDetails ? "button" : "div";
        return (
          <li key={`${event.timestamp}-${event.event}-${index}`} className="mb-4 last:mb-0">
            <span className={`absolute -left-2 mt-1 h-4 w-4 rounded-full border-2 border-white ${event.status === "success" ? "bg-green-500" : "bg-red-500"}`} />
            <CardElement
              type={hasErrorDetails ? "button" : undefined}
              onClick={hasErrorDetails ? () => onSelectError(event) : undefined}
              className={`flex w-full flex-col gap-1 rounded-xl bg-slate-50 p-3 text-left sm:flex-row sm:items-center sm:justify-between ${
                hasErrorDetails ? "cursor-pointer ring-1 ring-red-100 transition hover:bg-red-50 hover:ring-red-200" : ""
              }`}
            >
              <div>
                <p className="font-medium text-slate-900">{event.label}</p>
                <p className="text-xs text-slate-500">
                  {event.event} · {event.status} · {formatDateTime(event.timestamp, dashboard)}
                  {hasErrorDetails ? ` · ${dashboard.clickForDetails}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                {typeof event.duration_ms === "number" && <Badge>{event.duration_ms}ms</Badge>}
                {event.mode && <Badge>{event.mode}</Badge>}
                {event.model && <Badge>{event.model}</Badge>}
                {event.error_type && <Badge tone="red">{event.error_type}</Badge>}
              </div>
            </CardElement>
          </li>
        );
      })}
    </ol>
  );
}

function ErrorDetailsOverlay({
  event,
  dashboard,
  onClose,
}: {
  event: MetricsRecentEvent;
  dashboard: DashboardTranslations;
  onClose: () => void;
}) {
  const details = [
    [dashboard.event, event.event],
    [dashboard.status, event.status],
    [dashboard.label, event.label],
    [dashboard.time, formatDateTime(event.timestamp, dashboard)],
    [dashboard.route, [event.method, event.route].filter(Boolean).join(" ")],
    [dashboard.operation, event.operation],
    [dashboard.tool, event.tool_name],
    [dashboard.mode, event.mode],
    [dashboard.model, event.model],
    [dashboard.statusCode, event.status_code?.toString()],
    [dashboard.duration, typeof event.duration_ms === "number" ? `${event.duration_ms}ms` : ""],
    [dashboard.errorType, event.error_type],
  ].filter(([, value]) => value);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <section className="w-full max-w-2xl rounded-2xl border border-red-100 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-red-600">{dashboard.errorDetails}</p>
            <h2 className="mt-1 text-2xl font-bold text-slate-900">{event.label}</h2>
            <p className="mt-1 text-sm text-slate-500">
              {dashboard.sanitizedErrorMetadata}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-3 py-1 text-sm text-slate-700 transition hover:bg-slate-50"
          >
            {dashboard.close}
          </button>
        </div>
        <div className="grid gap-3 p-5">
          {details.map(([label, value]) => (
            <div key={label} className="grid gap-1 rounded-xl bg-slate-50 p-3 sm:grid-cols-[130px_1fr]">
              <dt className="text-sm font-medium text-slate-500">{label}</dt>
              <dd className="break-words text-sm text-slate-900">{value}</dd>
            </div>
          ))}
          <div className="rounded-xl border border-red-100 bg-red-50 p-4">
            <h3 className="text-sm font-semibold text-red-800">{dashboard.message}</h3>
            <p className="mt-2 whitespace-pre-wrap break-words text-sm text-red-900">
              {event.error_message || dashboard.noErrorMessage}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

function isErrorEvent(event: MetricsRecentEvent): boolean {
  return (
    event.status === "error" ||
    Boolean(event.error_type) ||
    Boolean(event.error_message) ||
    (typeof event.status_code === "number" && event.status_code >= 400)
  );
}

function Badge({ children, tone = "slate" }: { children: React.ReactNode; tone?: "slate" | "red" }) {
  return (
    <span className={`rounded-full px-2 py-1 ${tone === "red" ? "bg-red-100 text-red-700" : "bg-slate-200 text-slate-700"}`}>
      {children}
    </span>
  );
}

function resolveHealth(
  errorRate: number,
  rateLimitHits: number,
  dashboard: DashboardTranslations,
) {
  if (errorRate >= 0.1) {
    return { label: dashboard.degraded, className: "bg-red-100 text-red-700" };
  }
  if (errorRate >= 0.03 || rateLimitHits > 0) {
    return { label: dashboard.watch, className: "bg-amber-100 text-amber-800" };
  }
  return { label: dashboard.healthy, className: "bg-green-100 text-green-700" };
}

function formatNumber(value: number | undefined | null): string {
  return new Intl.NumberFormat("en", { maximumFractionDigits: 0 }).format(value ?? 0);
}

function formatPercent(value: number | undefined | null): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function formatHour(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], { hour: "2-digit" });
}

function formatDateTime(
  value: string | undefined,
  dashboard: DashboardTranslations,
): string {
  if (!value) {
    return dashboard.never;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
