self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open('pdf-summarizer-cache').then(function(cache) {
            return cache.addAll([
                '/',
                '/static/manifest.json',
                '/static/icons/icon-192x192.png',
                '/static/icons/icon-512x512.png',
                '/static/styles.css',  // Add other assets you want to cache
                '/static/scripts.js'   // Add other assets you want to cache
            ]);
        })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request).then(function(response) {
            return response || fetch(event.request);
        })
    );
});
