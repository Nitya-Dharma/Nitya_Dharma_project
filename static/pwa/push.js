/**
 * PWA push notification permission and helpers.
 * Call requestNotificationPermission() when user logs in or opens dashboard
 * (e.g. from a "Enable notifications" button or after login).
 */
(function (global) {
  "use strict";

  /**
   * Request notification permission. Resolves with "granted" | "denied" | "default".
   * @returns {Promise<string>}
   */
  function requestNotificationPermission() {
    if (!("Notification" in global)) {
      return Promise.resolve("unsupported");
    }
    if (Notification.permission === "granted") {
      return Promise.resolve("granted");
    }
    if (Notification.permission === "denied") {
      return Promise.resolve("denied");
    }
    return Notification.requestPermission().then(function (permission) {
      if (typeof console !== "undefined" && console.log) {
        if (permission === "granted") {
          console.log("Notifications allowed");
        } else {
          console.log("Notifications permission:", permission);
        }
      }
      return permission;
    });
  }

  /**
   * Whether the environment supports push and we have an active service worker registration.
   * @returns {Promise<boolean>}
   */
  function isPushSupported() {
    if (!("serviceWorker" in navigator) || !("PushManager" in global)) {
      return Promise.resolve(false);
    }
    return navigator.serviceWorker.ready.then(function (reg) {
      return !!reg;
    }).catch(function () {
      return false;
    });
  }

  /**
   * Register for background sync (tag: "sync-requests").
   * Call after queueing a request locally so the SW can retry when online.
   * @returns {Promise<boolean>}
   */
  function requestBackgroundSync() {
    if (!("serviceWorker" in navigator)) return Promise.resolve(false);
    return navigator.serviceWorker.ready.then(function (reg) {
      if ("sync" in reg) {
        return reg.sync.register("sync-requests").then(function () {
          return true;
        }).catch(function () {
          return false;
        });
      }
      return false;
    }).catch(function () {
      return false;
    });
  }

  var SYNC_QUEUE_DB = "nd-sync-queue";
  var SYNC_QUEUE_STORE = "requests";

  /**
   * Add a request to the background-sync queue (same store the SW reads).
   * Then calls requestBackgroundSync() so the worker replays when online.
   * @param {{ url: string, method?: string, headers?: object, body?: string }} obj
   * @returns {Promise<void>}
   */
  function addToSyncQueue(obj) {
    if (!("indexedDB" in global)) return Promise.resolve();
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(SYNC_QUEUE_DB, 1);
      req.onerror = function () { reject(req.error); };
      req.onsuccess = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(SYNC_QUEUE_STORE)) {
          db.close();
          return resolve();
        }
        var tx = db.transaction(SYNC_QUEUE_STORE, "readwrite");
        var store = tx.objectStore(SYNC_QUEUE_STORE);
        store.add({
          url: obj.url,
          method: obj.method || "GET",
          headers: obj.headers || undefined,
          body: obj.body || undefined
        });
        tx.oncomplete = function () {
          db.close();
          requestBackgroundSync();
          resolve();
        };
        tx.onerror = function () { reject(tx.error); };
      };
      req.onupgradeneeded = function (e) {
        var db = e.target.result;
        if (!db.objectStoreNames.contains(SYNC_QUEUE_STORE)) {
          db.createObjectStore(SYNC_QUEUE_STORE, { keyPath: "id", autoIncrement: true });
        }
      };
    }).catch(function () {});
  }

  // Export for use from dashboard / login pages
  global.NDPWA = global.NDPWA || {};
  global.NDPWA.requestNotificationPermission = requestNotificationPermission;
  global.NDPWA.isPushSupported = isPushSupported;
  global.NDPWA.requestBackgroundSync = requestBackgroundSync;
  global.NDPWA.addToSyncQueue = addToSyncQueue;

  // Show "Enable notifications" button when permission not yet set; handle click
  function initNotifyButton() {
    var btn = typeof document !== "undefined" && document.getElementById("enableNotificationsButton");
    if (!btn || !("Notification" in global)) return;
    if (Notification.permission === "default") {
      btn.style.display = "inline-block";
      btn.setAttribute("aria-hidden", "false");
    }
    btn.addEventListener("click", function () {
      requestNotificationPermission().then(function () {
        btn.style.display = "none";
        btn.setAttribute("aria-hidden", "true");
      });
    });
  }
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initNotifyButton);
    } else {
      initNotifyButton();
    }
  }
})(typeof window !== "undefined" ? window : this);
