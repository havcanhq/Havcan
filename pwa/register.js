/**
 * Register the PWA service worker when the browser supports it.
 * Registration failures are non-fatal to the existing HAVCAN experience.
 */
(function () {
  'use strict';

  if (!('serviceWorker' in navigator)) return;

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('./service-worker.js', { scope: './' })
      .catch(function (error) {
        if (window.HavcanAppState) {
          window.HavcanAppState.setError(`PWA registration failed: ${error.message}`);
        }
      });
  });
})();