/**
 * Shared loading/error state boundary for future API-backed screens.
 *
 * Existing UI screens do not depend on this yet, so Phase 1 preserves their
 * current behavior while giving future features one consistent state model.
 */
(function (global) {
  'use strict';

  let state = Object.freeze({ loading: false, error: null });
  const listeners = new Set();

  function notify() {
    listeners.forEach((listener) => listener(state));
  }

  function setState(next) {
    state = Object.freeze({ ...state, ...next });
    notify();
    return state;
  }

  global.HavcanAppState = Object.freeze({
    get: () => state,
    subscribe(listener) {
      listeners.add(listener);
      listener(state);
      return () => listeners.delete(listener);
    },
    setLoading: (loading) => setState({ loading: Boolean(loading) }),
    setError: (error) => setState({ error: error ? String(error) : null }),
    clearError: () => setState({ error: null }),
    async withLoading(work) {
      setState({ loading: true, error: null });
      try {
        return await work();
      } catch (error) {
        setState({ error: error.message || String(error) });
        throw error;
      } finally {
        setState({ loading: false });
      }
    },
  });
})(window);