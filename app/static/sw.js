// MyTodo Service Worker —— 极简版：只缓存静态资源，不碰 API
// 静态资源（tailwind.js/favicon/图标/字体）缓存优先，API 永远走网络
const CACHE = 'mytodo-v1';
const STATIC_ASSETS = [
  '/static/tailwind.js',
  '/static/favicon.svg',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/apple-touch-icon.png',
];

// 安装：预缓存静态资源，立即激活
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()));
});

// 激活：清理旧缓存
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

// 请求拦截：静态资源缓存优先，API 和页面永远走网络
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // 只处理同源 GET
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return;
  // API 请求：永远网络（数据必须实时）
  if (url.pathname.startsWith('/api/')) return;
  // HTML 页面：网络优先（保证拿到最新版本），失败才回退缓存
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    return;
  }
  // 静态资源：缓存优先，缺失才网络并缓存
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request).then(resp => {
      if (resp.ok) {
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return resp;
    }))
  );
});
