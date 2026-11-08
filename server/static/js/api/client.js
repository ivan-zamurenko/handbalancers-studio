import {beginLoading} from '../components/loading.js';

const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS']);
const jsonBodyTypes = new Set(['[object Object]', '[object Array]']);

export class ApiError extends Error {
  constructor(status, error = {}) {
    super(error.message_key || `Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.code = error.code || 'http_error';
    this.messageKey = error.message_key || 'errors.http_error';
    this.fieldErrors = Array.isArray(error.field_errors) ? error.field_errors : [];
    this.requestId = error.request_id || null;
  }
}

export class NetworkError extends Error {
  constructor(cause) {
    super('Network request failed', { cause });
    this.name = 'NetworkError';
    this.kind = 'network';
  }
}

function getCsrfToken(documentObject) {
  return documentObject?.querySelector?.('meta[name="csrf-token"]')?.content || null;
}

function isJsonBody(body) {
  if (!body || typeof body !== 'object') return false;
  if (typeof FormData !== 'undefined' && body instanceof FormData) return false;
  if (typeof URLSearchParams !== 'undefined' && body instanceof URLSearchParams) return false;
  if (typeof Blob !== 'undefined' && body instanceof Blob) return false;
  if (typeof ArrayBuffer !== 'undefined' && body instanceof ArrayBuffer) return false;
  return jsonBodyTypes.has(Object.prototype.toString.call(body));
}

export async function requestApi(input, {
  baseUrl = globalThis.location?.origin || 'http://localhost',
  csrfToken,
  loading = 'background',
  fetchImpl = globalThis.fetch,
  documentObject = globalThis.document,
  ...requestOptions
} = {}) {
  const base = new URL(baseUrl);
  const url = new URL(input, base);
  const sameOrigin = url.origin === base.origin;
  const method = (requestOptions.method || 'GET').toUpperCase();
  const headers = new Headers(requestOptions.headers);
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');

  const body = requestOptions.body;
  const options = { ...requestOptions, method, headers };
  if (isJsonBody(body)) {
    options.body = JSON.stringify(body);
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  }

  const token = csrfToken ?? getCsrfToken(documentObject);
  if (sameOrigin && !safeMethods.has(method) && token && !headers.has('X-CSRF-Token')) {
    headers.set('X-CSRF-Token', token);
  }
  options.credentials = sameOrigin ? 'same-origin' : 'omit';

  const finishLoading = beginLoading(typeof loading === 'string' ? {mode:loading} : loading);
  try {
    let response;
    try {
      response = await fetchImpl(url, options);
    } catch (cause) {
      throw new NetworkError(cause);
    }

    if (!response.ok) {
      let payload;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      throw new ApiError(response.status, payload?.error);
    }

    if (response.status === 204) return null;
    if (response.headers.get('content-type')?.includes('application/json')) {
      return await response.json();
    }
    return await response.text();
  } finally {
    finishLoading();
  }
}
