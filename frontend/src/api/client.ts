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

interface RequestOptions extends RequestInit {
  retryOnElevation?: boolean;
}

export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { retryOnElevation = true, ...fetchOptions } = options;

  const headers = new Headers(fetchOptions.headers || {});
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  // Auto-set Content-Type for JSON objects
  if (fetchOptions.body && typeof fetchOptions.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const config: RequestInit = {
    ...fetchOptions,
    headers,
    credentials: 'include', // Ensures lavender_session cookie is sent
  };

  const response = await fetch(endpoint, config);

  if (response.status === 403 && retryOnElevation && onElevationRequired) {
    const errorClone = response.clone();
    let detail = '';
    try {
      const errJson = await errorClone.json();
      detail = errJson.detail || '';
    } catch {
      // not JSON
    }

    if (detail.toLowerCase().includes('admin') || detail.toLowerCase().includes('elevate')) {
      const elevated = await onElevationRequired();
      if (elevated) {
        // Retry the request once with elevated privileges
        return apiFetch<T>(endpoint, { ...options, retryOnElevation: false });
      }
    }
  }

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}`;
    let errorData = null;
    try {
      errorData = await response.json();
      if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
        errorMessage = String((errorData as { detail: unknown }).detail);
      }
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    throw new ApiError(response.status, errorMessage, errorData);
  }

  // Handle empty responses (like 204 or empty POST)
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

export const api = {
  get: <T>(url: string, options?: RequestOptions) =>
    apiFetch<T>(url, { ...options, method: 'GET' }),
  post: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(url, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(url: string, options?: RequestOptions) =>
    apiFetch<T>(url, { ...options, method: 'DELETE' }),
};
