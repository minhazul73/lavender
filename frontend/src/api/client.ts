export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

type ElevationHandler = () => Promise<boolean>;

let onElevationRequired: ElevationHandler | null = null;

export function registerElevationHandler(handler: ElevationHandler) {
  onElevationRequired = handler;
}

export function unregisterElevationHandler() {
  onElevationRequired = null;
}

export interface RequestOptions extends RequestInit {
  json?: unknown;
  retryOnElevation?: boolean;
  timeoutMs?: number;
}

function resolveRequestSignal(signal?: AbortSignal | null, timeoutMs = 15000): AbortSignal | undefined {
  if (signal) {
    return signal;
  }
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(timeoutMs);
  }
  return undefined;
}

function prepareRequestHeadersAndBody(
  initHeaders?: HeadersInit,
  initBody?: BodyInit | null,
  json?: unknown
): { headers: Headers; body: BodyInit | null | undefined } {
  const headers = new Headers(initHeaders || {});
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  let body: BodyInit | null | undefined = initBody;
  if (json !== undefined) {
    body = JSON.stringify(json);
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
  }

  return { headers, body };
}

type ElevationRetryResult<T> =
  | { retried: false }
  | { retried: true; value: T };

async function handleElevationRetry<T>(
  endpoint: string,
  response: Response,
  options: RequestOptions
): Promise<ElevationRetryResult<T>> {
  if (!onElevationRequired) {
    return { retried: false };
  }

  let detail = '';
  try {
    const errJson = await response.clone().json();
    detail = errJson?.detail || '';
  } catch {
    // Response body not JSON
  }

  const isElevationError =
    detail.toLowerCase().includes('admin') || detail.toLowerCase().includes('elevate');
  if (!isElevationError) {
    return { retried: false };
  }

  const elevated = await onElevationRequired();
  if (!elevated) {
    return { retried: false };
  }

  const value = await apiFetch<T>(endpoint, options);
  return { retried: true, value };
}

async function parseErrorResponse(response: Response): Promise<{ message: string; data: unknown }> {
  let errorMessage = `HTTP Error ${response.status}`;
  let errorData: unknown = null;
  try {
    errorData = await response.json();
    if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
      errorMessage = String((errorData as { detail: unknown }).detail);
    }
  } catch {
    errorMessage = response.statusText || errorMessage;
  }
  return { message: errorMessage, data: errorData };
}

async function parseResponseBody<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const {
    json,
    retryOnElevation = true,
    timeoutMs = 15000,
    signal,
    headers: initHeaders,
    body: initBody,
    ...fetchOptions
  } = options;

  const { headers, body } = prepareRequestHeadersAndBody(initHeaders, initBody, json);
  const requestSignal = resolveRequestSignal(signal, timeoutMs);

  const config: RequestInit = {
    ...fetchOptions,
    body,
    headers,
    signal: requestSignal,
    credentials: 'include', // Ensures lavender_session cookie is sent
  };

  const response = await fetch(endpoint, config);

  if (response.status === 403 && retryOnElevation) {
    const { json: _ignored, ...optionsWithoutJson } = options;
    const retryOptions: RequestOptions = {
      ...optionsWithoutJson,
      headers,
      body,
      retryOnElevation: false,
    };
    const retryResult = await handleElevationRetry<T>(endpoint, response, retryOptions);
    if (retryResult.retried) {
      return retryResult.value;
    }
  }

  if (!response.ok) {
    const { message, data } = await parseErrorResponse(response);
    throw new ApiError(response.status, message, data);
  }

  return parseResponseBody<T>(response);
}

export const api = {
  get: <T>(url: string, options?: RequestOptions) =>
    apiFetch<T>(url, { ...options, method: 'GET' }),
  post: <T>(url: string, body?: unknown, options?: RequestOptions) => {
    const postOptions: RequestOptions = { ...options, method: 'POST' };
    if (body instanceof FormData) {
      postOptions.body = body;
      delete postOptions.json;
    } else if (body !== undefined) {
      postOptions.json = body;
      delete postOptions.body;
    }
    return apiFetch<T>(url, postOptions);
  },
  postForm: <T>(url: string, formData: FormData, options?: RequestOptions) =>
    apiFetch<T>(url, {
      ...options,
      method: 'POST',
      body: formData,
    }),
  delete: <T>(url: string, options?: RequestOptions) =>
    apiFetch<T>(url, { ...options, method: 'DELETE' }),
};
