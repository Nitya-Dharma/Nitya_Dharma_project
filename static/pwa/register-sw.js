/**
 * Register the PWA service worker.
 * Runs on load; install prompt is handled by a2hs.js.
 */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker
      .register("/service-worker.js")
      .then(function (registration) {
        if (typeof console !== "undefined" && console.log) {
          console.log("Service Worker registered:", registration.scope);
        }
      })
      .catch(function (error) {
        if (typeof console !== "undefined" && console.warn) {
          console.warn("Service Worker registration failed:", error);
        }
      });
  });
}
