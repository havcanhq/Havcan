/**
 * Small, dependency-free API client boundary for the existing HAVCAN UI.
 *
 * It remains small and dependency-free so the existing single-file UI can
 * progressively adopt real API-backed features without a framework rewrite.
 */
(function (global) {
  'use strict';

  const DEFAULT_BASE_URL = '/api';

  function getBaseUrl() {
    return (global.HAVCAN_API_BASE_URL || DEFAULT_BASE_URL).replace(/\/$/, '');
  }

  async function request(path, options) {
    const requestOptions = { ...(options || {}), credentials: 'include' };
    if (requestOptions.body && typeof requestOptions.body !== 'string') {
      requestOptions.body = JSON.stringify(requestOptions.body);
      requestOptions.headers = {
        'Content-Type': 'application/json',
        ...(requestOptions.headers || {}),
      };
    }

    const response = await fetch(`${getBaseUrl()}${path}`, {
      ...requestOptions,
      headers: {
        Accept: 'application/json',
        ...(requestOptions.headers || {}),
      },
    });

    const contentType = response.headers.get('content-type') || '';
    const body = response.status === 204
      ? null
      : contentType.includes('application/json')
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
    register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
    login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
    logout: () => request('/auth/logout', { method: 'POST' }),
    me: () => request('/auth/me'),
    forgotPassword: (payload) => request('/auth/forgot-password', { method: 'POST', body: payload }),
    resetPassword: (payload) => request('/auth/reset-password', { method: 'POST', body: payload }),
  });
})(window);