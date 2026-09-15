/**
 * Small, dependency-free API client boundary for the existing HAVCAN UI.
 *
 * It is intentionally opt-in: Phase 1 does not replace the current mock
 * interactions or introduce business-domain requests.
 */
(function (global) {
  'use strict';

  const DEFAULT_BASE_URL = '/api';

  function getBaseUrl() {
    return (global.HAVCAN_API_BASE_URL || DEFAULT_BASE_URL).replace(/\/$/, '');
  }

  async function request(path, options) {
    const response = await fetch(`${getBaseUrl()}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options && options.headers ? options.headers : {}),
      },
    });

    const contentType = response.headers.get('content-type') || '';
    const body = contentType.includes('application/json')
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const detail = body && typeof body === 'object' && body.detail
        ? body.detail
        : `Request failed with status ${response.status}`;
      const error = new Error(detail);
      error.status = response.status;
      error.body = body;
      throw error;
    }

    return body;
  }

  global.HavcanAPI = Object.freeze({
    request,
    health: () => request('/health'),
  });
})(window);