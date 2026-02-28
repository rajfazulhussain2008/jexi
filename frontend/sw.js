// Service Worker for JEXI PWA
const CACHE_NAME = 'jexi-cache-v1';
const ASSETS = [
    '/',
    '/index.html',
    '/css/style.css',
    '/js/app.js',
    '/js/utils.js',
    '/js/api.js',
    '/js/chat.js',
    '/js/notifications.js',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'
];

// Install Event - Cache assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
});

// Activate Event - Clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            );
        })
    );
});

// Fetch Event - Serve from cache first, then network
self.addEventListener('fetch', (event) => {
    // Only cache GET requests
    if (event.request.method !== 'GET') return;

    // Don't cache API calls - handled by local storage/DB
    if (event.request.url.includes('/api/v1')) return;

    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            return cachedResponse || fetch(event.request);
        })
    );
});

// Push Notification Event
self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : { title: 'JEXI Update', message: 'Something new happened!' };

    const options = {
        body: data.message,
        icon: 'https://ui-avatars.com/api/?name=JEXI&background=8B5CF6&color=fff&size=192',
        badge: 'https://ui-avatars.com/api/?name=J&background=8B5CF6&color=fff&size=96',
        vibrate: [100, 50, 100],
        data: {
            url: '/'
        }
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification Click Event
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});
