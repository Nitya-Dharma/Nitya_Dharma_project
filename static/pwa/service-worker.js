/**
 * Nitya Dharma PWA Service Worker
 * Supports: static cache, runtime cache, images, search caching, offline fallback,
 * push notifications, background sync.
 * Note: When served from /static/pwa/, scope is limited to /static/pwa/.
 * For full-site control (e.g. offline /), serve this file from site root.
 */
const STATIC_CACHE = "nd-static-v1";
const RUNTIME_CACHE = "nd-runtime-v1";
const SYNC_QUEUE_DB = "nd-sync-queue";
const SYNC_QUEUE_STORE = "requests";

const STATIC_ASSETS = [
  "/",
  "/offline/",
  "/static/css/theme.css",
  "/static/css/navbar_premium.css",
  "/static/css/footer_premium.css",
  "/static/css/navbar_dark_mode_fix.css",
  "/static/css/mobile-responsive.css",
  "/static/pwa/manifest.json",
  "/static/pwa/icons/icon-192.png",
  "/static/pwa/icons/icon-512.png"
];

// --- Install: precache static assets ---
self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(function (cache) {
      return cache.addAll(STATIC_ASSETS).catch(function () {});
    })
  );
  self.skipWaiting();
});

// --- Activate: prune old caches ---
self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (cacheNames) {
      return Promise.all(
        cacheNames
          .filter(function (name) {
            return name !== STATIC_CACHE && name !== RUNTIME_CACHE;
          })
          .map(function (name) {
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// --- Fetch: strategies by type ---
self.addEventListener("fetch", function (event) {
  var url = event.request.url;
  var dest = event.request.destination;
  var isNav = event.request.mode === "navigate";

  // Images: cache-first (runtime)
  if (dest === "image") {
    event.respondWith(
      caches.open(RUNTIME_CACHE).then(function (cache) {
        return cache.match(event.request).then(function (response) {
          if (response) return response;
          return fetch(event.request).then(function (networkResponse) {
            if (networkResponse && networkResponse.status === 200) {
              cache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          });
        });
      })
    );
    return;
  }

  // Search pages: network-first, cache on success, fallback to cache then offline
  if (url.indexOf("/search") !== -1 && isNav) {
    event.respondWith(
      fetch(event.request)
        .then(function (response) {
          var cloned = response.clone();
          caches.open(RUNTIME_CACHE).then(function (cache) {
            cache.put(event.request, cloned);
          });
          return response;
        })
        .catch(function () {
          return caches.match(event.request).then(function (cached) {
            if (cached) return cached;
            return caches.match("/offline/").then(function (offline) {
              return offline || new Response("Offline", { status: 503, statusText: "Offline" });
            });
          });
        })
    );
    return;
  }

  // Other requests: network first, fallback cache; for navigation fallback to offline
  event.respondWith(
    fetch(event.request)
      .then(function (response) {
        if (response && response.status === 200 && (dest === "document" || dest === "script" || dest === "style")) {
          var clone = response.clone();
          caches.open(RUNTIME_CACHE).then(function (cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      })
      .catch(function () {
        return caches.match(event.request).then(function (cached) {
          if (cached) return cached;
          if (isNav) {
            return caches.match("/offline/").then(function (offline) {
              return offline || new Response("Offline", { status: 503, statusText: "Offline" });
            });
          }
          return new Response("Offline", { status: 503, statusText: "Offline" });
        });
      })
  );
});

// --- Background Sync: replay queued requests ---
function openSyncDB() {
  return new Promise(function (resolve, reject) {
    var req = indexedDB.open(SYNC_QUEUE_DB, 1);
    req.onerror = function () { reject(req.error); };
    req.onsuccess = function () { resolve(req.result); };
    req.onupgradeneeded = function (e) {
      var db = e.target.result;
      if (!db.objectStoreNames.contains(SYNC_QUEUE_STORE)) {
        db.createObjectStore(SYNC_QUEUE_STORE, { keyPath: "id", autoIncrement: true });
      }
    };
  });
}

function getStoredRequests() {
  return openSyncDB().then(function (db) {
    return new Promise(function (resolve, reject) {
      var tx = db.transaction(SYNC_QUEUE_STORE, "readonly");
      var store = tx.objectStore(SYNC_QUEUE_STORE);
      var req = store.getAll();
      req.onsuccess = function () { resolve(req.result || []); };
      req.onerror = function () { reject(req.error); };
    });
  }).catch(function () { return []; });
}

function clearStoredRequests(ids) {
  if (!ids.length) return Promise.resolve();
  return openSyncDB().then(function (db) {
    var tx = db.transaction(SYNC_QUEUE_STORE, "readwrite");
    var store = tx.objectStore(SYNC_QUEUE_STORE);
    ids.forEach(function (id) { store.delete(id); });
    return new Promise(function (resolve, reject) {
      tx.oncomplete = resolve;
      tx.onerror = function () { reject(tx.error); };
    });
  });
}

function syncQueuedRequests() {
  return getStoredRequests().then(function (queue) {
    var done = [];
    return Promise.all(
      queue.map(function (item) {
        var url = item.url;
        var options = { method: item.method || "GET", credentials: "same-origin" };
        if (item.headers) options.headers = item.headers;
        if (item.body) options.body = item.body;
        return fetch(url, options)
          .then(function () { done.push(item.id); })
          .catch(function () {});
      })
    ).then(function () {
      return clearStoredRequests(done);
    });
  });
}

self.addEventListener("sync", function (event) {
  if (event.tag === "sync-requests") {
    event.waitUntil(syncQueuedRequests());
  }
});

// --- Push notifications ---
self.addEventListener("push", function (event) {
  var data = { title: "Nitya Dharma", body: "You have a new update." };
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }
  var options = {
    body: data.body,
    icon: "/static/pwa/icons/icon-192.png",
    badge: "/static/pwa/icons/icon-192.png",
    data: { url: data.url || "/" }
  };
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var url = event.notification.data && event.notification.data.url ? event.notification.data.url : "/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clientList) {
      for (var i = 0; i < clientList.length; i++) {
        if (clientList[i].url.indexOf(self.location.origin) !== -1 && "focus" in clientList[i]) {
          clientList[i].navigate(url);
          return clientList[i].focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});
