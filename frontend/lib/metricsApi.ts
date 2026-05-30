import { buildApiUrl } from "./appLogic.mjs";
import type { MetricsResponse } from "../types/app";

export type ApiResult<T> = {
  ok: boolean;
  data: T;
};

export async function fetchMetrics(
  apiBaseUrl: string,
  options: { windowHours?: number; recentLimit?: number } = {},
): Promise<ApiResult<MetricsResponse>> {
  const params = new URLSearchParams();
  if (options.windowHours) {
    params.set("window_hours", String(options.windowHours));
  }
  if (options.recentLimit !== undefined) {
    params.set("recent_limit", String(options.recentLimit));
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(buildApiUrl(apiBaseUrl, `/api/metrics${suffix}`));
  return {
    ok: response.ok,
    data: (await response.json()) as MetricsResponse,
  };
}
