const CACHE_NAME = 'apryse-viewer-cache-v2'; // Use a new version name

// This event runs when the service worker is first installed.
self.addEventListener('install', event => {
  // skipWaiting() forces the waiting service worker to become the active one.
  event.waitUntil(self.skipWaiting()); 
});

// This event runs when the service worker is activated.
self.addEventListener('activate', event => {
  // A good practice is to clean up old caches.
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  // claim() makes the service worker take control of the page immediately.
  return self.clients.claim();
});


// This is the core logic: intercepting network requests.
self.addEventListener('fetch', event => {
  // Only handle GET requests and only for Apryse assets to avoid caching API calls.
  if (event.request.method !== 'GET' || !event.request.url.includes('/static/lib/apryse/')) {
    // For anything else, just fetch from the network as usual.
    return;
  }

  // Strategy: Cache then Network.
  event.respondWith(
    caches.open(CACHE_NAME).then(cache => {
      return cache.match(event.request).then(response => {
        // If we have a match in the cache, return it immediately.
        if (response) {
          // console.log('Service Worker: Serving from cache:', event.request.url);
          return response;
        }

        // If not in cache, fetch from the network.
        // console.log('Service Worker: Fetching from network and caching:', event.request.url);
        return fetch(event.request).then(networkResponse => {
          // Put a copy of the network response into the cache for next time.
          // We need to clone the response because it can only be consumed once.
          cache.put(event.request, networkResponse.clone());
          
          // Return the original response to the browser.
          return networkResponse;
        });
      });
    })
  );
});