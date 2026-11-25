export const SUPPORTED_METRICS = [
  'cpu',
  'ram',
  'thermal',
  'battery',
  'network',
] as const;

export type SupportedMetric = (typeof SUPPORTED_METRICS)[number];

export const DEFAULT_SSE_METRICS_QUERY = `metrics=${SUPPORTED_METRICS.join(',')}`;

export const DEFAULT_SSE_URL = `/api/device/live?${DEFAULT_SSE_METRICS_QUERY}`;
