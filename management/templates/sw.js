console.log("[SW] loaded");

self.addEventListener("push", function (event) {
    console.log("[SW] Push event:", event);

	let data = {};
	try {
		if (event.data) {
			data = event.data.json();
		}
	} catch (e) {
		console.error("[SW] Error parsing push data:", e);
	}

	const title = data.title || "Thông báo mới";
	const body = data.body || "";
	const url = data.url || "/";

	const options = {
		body: body,
		data: { url: url },
		icon: "/static/images/fec-logo-192.png", // nếu có icon PWA nhỏ
		badge: "/static/images/fec-logo-64.png", // tuỳ
	};

	event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", function (event) {
	event.notification.close();
	const url = (event.notification.data && event.notification.data.url) || "/";
	event.waitUntil(
		clients
			.matchAll({ type: "window", includeUncontrolled: true })
			.then(function (clientList) {
				for (const client of clientList) {
					if ("focus" in client) {
						client.navigate(url);
						return client.focus();
					}
				}
				if (clients.openWindow) {
					return clients.openWindow(url);
				}
			})
	);
});
