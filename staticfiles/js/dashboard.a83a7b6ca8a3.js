// Luôn có toast ở phạm vi global
(function () {
	// Nếu đã có thì không ghi đè
	if (window.toast) return;

	window.toast = function (msg, ms = 3000) {
		const el = document.createElement("div");
		el.className = "alert alert-success position-fixed shadow";
		el.style.right = "16px";
		el.style.bottom = "16px";
		el.style.zIndex = 9999;
		el.textContent = msg;
		document.body.appendChild(el);
		setTimeout(() => el.remove(), ms);
	};
})();

document.addEventListener("DOMContentLoaded", () => {
	const proto = location.protocol === "https:" ? "wss" : "ws";
	const ws = new WebSocket(`${proto}://${location.host}/ws/hub/`);

	const notify = (m) => (window.toast ? window.toast(m) : alert(m));
	const toast = window.toast || ((m) => console.log("[toast]", m));

	// ==== 1) Biến trạng thái cho Notification API ====
	let notificationEnabled = false;

	function initNotificationPermission() {
		if (!("Notification" in window)) {
			console.warn("Trình duyệt không hỗ trợ Notification API");
			return;
		}
		if (Notification.permission === "granted") {
			notificationEnabled = true;
			return;
		}
		if (Notification.permission === "denied") {
			console.warn("User đã chặn thông báo cho site này.");
			return;
		}
		// "default" -> chưa quyết → ta *có thể* xin quyền.
		// Tốt nhất là gắn với 1 hành động user (click nút).
	}

	const btnEnable = document.getElementById("btn-enable-noti");
	if (btnEnable && "Notification" in window) {
		btnEnable.addEventListener("click", () => {
			if (Notification.permission === "granted") {
				notificationEnabled = true;
				toast("Thông báo trình duyệt đã được bật.");
				return;
			}
			if (Notification.permission === "denied") {
				alert(
					"Bạn đã chặn thông báo cho trang này trong trình duyệt. Vui lòng vào cài đặt site để mở lại."
				);
				return;
			}
			Notification.requestPermission().then((perm) => {
				if (perm === "granted") {
					notificationEnabled = true;
					toast("Đã bật thông báo trình duyệt.");
				} else {
					toast("Bạn đã không cho phép thông báo.");
				}
			});
		});
	}
	// Khởi tạo (chỉ check, không tự động xin permission)
	initNotificationPermission();

	// ==== 2) Hàm hiển thị notification cho các sự kiện WS ====
	function showWSNotification(msg) {
		if (!("Notification" in window)) return;
		if (!notificationEnabled && Notification.permission !== "granted") {
			// Chưa cho phép thì thôi, đừng làm phiền.
			return;
		}
		let title = "";
		let body = "";
		let url = null;
		switch (msg.kind) {
			case "customer_created":
				title = "Khách hàng mới đăng ký";
				body =
					(msg.full_name || msg.name || "") +
					(msg.phone || msg.phone_number
						? " - " + (msg.phone || msg.phone_number)
						: "");
				url = msg.detail_url || msg.dashboard_url || null;
				break;

			case "signature_confirmed":
				title = "Khách hàng đã ký xác nhận";
				body =
					(msg.full_name || "") +
					(msg.phone_number ? " - " + msg.phone_number : "");
				url = msg.detail_url || null;
				break;

			case "approval_request":
				title = "Yêu cầu phê duyệt thông tin";
				body =
					`KH: ${msg.customer_name} (#${msg.customer_id})` +
					(msg.code ? ` - Mã: ${msg.code}` : "");
				// mở trang dashboard hoặc chi tiết
				url = msg.detail_url || window.location.origin + "/dashboard/";
				break;

			default:
				return; // các loại khác không cần notify
		}

		try {
			const n = new Notification(title, {
				body: body || "",
				// tag dùng để tránh spam nhiều notification giống nhau
                tag: `fec-${msg.kind}-${msg.id || msg.customer_id || Date.now()}`,
			});

            n.onclick = (ev) => {
                ev.preventDefault();
                window.focus();
                if (url) {
                    window.open(url, "_blank", );
                }
                n.close();
            }
		} catch (err) {
			console.error("Lỗi khi hiển thị notification:", err);
		}
	}

	ws.onopen = () => console.log("WS open (hub)");
	ws.onclose = (e) => console.warn("WS closed:", e.code);
	ws.onerror = (e) => console.error("WS error", e);

	ws.onmessage = (e) => {
		let msg;
		try {
			msg = JSON.parse(e.data);
		} catch {
			return;
		}

		switch (msg.kind) {
			// === Dashboard events ===
			case "customer_created":
			case "signature_confirmed":
				if (typeof updateOrPrependRow === "function") {
					updateOrPrependRow(msg);
				}
				toast(
					msg.kind === "customer_created"
						? `Có khách mới: ${msg.full_name || msg.phone_number || ""}`
						: `KHÁCH ĐÃ KÝ: ${msg.full_name || msg.phone_number || ""}`
				);
				// 🔔 Thêm: notification trình duyệt
                showWSNotification(msg);
				break;

			// === Manager approval events (mã 6 số) ===
			case "approve_request":
				// CHỈ hiển thị toast này cho Manager.
				// Biến window.IS_USER_MANAGER được giả định là đã được set trong template HTML.
				if (window.IS_USER_MANAGER) {
					// Hiển thị toast/modal để Manager thấy mã phê duyệt
					const html = `
					<div class="alert alert-info alert-dismissible fade show"
						role="alert"
						style="position:fixed;right:12px;bottom:12px;z-index:2000;max-width:360px">
						<div><strong>Yêu cầu phê duyệt</strong></div>
						<div>KH: ${msg.customer_name} (#${msg.customer_id})</div>
						<div>Mã: <b>${msg.code}</b></div>
						<div class="small text-muted">Hết hạn: ${new Date(
							msg.expires_at
						).toLocaleString()}</div>
						<div class="small text-muted">Yêu cầu bởi: ${msg.requested_by}</div>
						<button type="button" class="btn-close" data-bs-dismiss="alert"></button>
					</div>`;
					document.body.insertAdjacentHTML("beforeend", html);

					// 🔔 Thêm: notification trình duyệt
                    showWSNotification(msg);
				}
				break;

			case "update_customer":
				if (msg.result_update === "success" && window.IS_USER_MANAGER) {
					window.location.reload();
				}
				break;

			case "ws_ready":
				// tuỳ chọn: đánh dấu sẵn sàng
				break;

			case "error":
				console.error("WS server error:", msg.where, msg.detail);
				notify("Realtime lỗi: " + (msg.detail || ""));
				break;
		}
	};
});

// Chèn dòng mới vào bảng thay vì reload
function prependRow(m) {
	const tbody = document.querySelector("table tbody");
	if (!tbody) return;

	// Xoá dòng "Chưa có dữ liệu" nếu có
	const empty = tbody.querySelector("td[colspan]");
	if (empty && empty.parentElement) empty.parentElement.remove();

	const esc = (v) => {
		const d = document.createElement("div");
		d.textContent = v ?? "";
		return d.innerHTML;
	};

	const tr = document.createElement("tr");
	tr.setAttribute("data-id", String(m.id));

	tr.innerHTML = `
        <td>•</td>
        <td>${esc(m.name)}</td>
        <td>${esc(m.gender)}</td>
        <td>${esc(m.phone)}</td>
        <td>${esc(m.id_card || "")}</td>
        <td>${esc(m.permanent_address || "")}</td>
        <td>${esc(m.income || "")}</td>
        <td>${esc(m.loan_amount || "")}</td>
        <td>${esc(m.created_at || "")}</td>
        <td data-col="pdf">${
				m.has_pdf
					? m.pdf_url
						? `<a href="${m.pdf_url}" target="_blank" rel="noopener">PDF</a>`
						: "Có"
					: "Không"
			}</td>
    `;
	tbody.prepend(tr);
}

function formatVnCurrency(amount, currency = "VND") {
	const n = Number(amount);
	if (!Number.isFinite(n)) return String(amount ?? "");
	const body = new Intl.NumberFormat("de-DE", {
		maximumFractionDigits: 0,
	}).format(Math.trunc(n));
	return `${body} ${currency}`;
}

function formatVnPhone(phone) {
	if (
		typeof phone === "string" &&
		phone.startsWith("84") &&
		phone.length === 11
	) {
		const local = "0" + phone.slice(2);
		return `${local.slice(0, 4)} ${local.slice(4, 7)} ${local.slice(7)}`;
	}
	return phone ?? "";
}

function escText(v) {
	const d = document.createElement("div");
	d.textContent = v ?? "";
	return d.textContent;
}

function buildPdfCellStyled(hasPdf, pdfDownloadUrl) {
	const td = document.createElement("td");
	td.className = "text-center";
	td.setAttribute("data-col", "pdf");

	if (hasPdf) {
		const a = document.createElement("a");
		a.className = "btn btn-sm btn-danger";
		a.title = "Tải văn bản xác nhận (PDF)";
		a.textContent = "Tải PDF";
		a.href = pdfDownloadUrl || "#";
		a.target = "_blank";
		a.rel = "noopener";
		td.appendChild(a);
	} else {
		const span = document.createElement("span");
		span.className = "badge bg-secondary";
		span.textContent = "Chưa có";
		td.appendChild(span);
	}
	return td;
}

function buildDetailCell(detailUrl) {
	const td = document.createElement("td");
	td.className = "text-center";
	td.setAttribute("data-col", "detail");
	const a = document.createElement("a");
	a.className = "btn btn-sm btn-primary";
	a.textContent = "Chi tiết";
	a.href = detailUrl || "#";
	td.appendChild(a);
	return td;
}

function buildEditCell(customerId) {
	const td = document.createElement("td");
	td.className = "text-center";
	td.setAttribute("data-col", "edit");
	const button = document.createElement("button");
	button.type = "button";
	button.className = "btn btn-sm btn-warning btn-edit";
	button.textContent = "Chỉnh Sửa";
	button.setAttribute("data-id", customerId);
	td.appendChild(button);
	return td;
}

function buildRowStyled(m) {
	const tr = document.createElement("tr");
	tr.setAttribute("data-id", String(m.id));

	// Cột 1: id
	let td = document.createElement("td");
	td.setAttribute("data-col", "id");
	td.textContent = escText(m.id);
	tr.appendChild(td);

	// 2: full_name
	td = document.createElement("td");
	td.setAttribute("data-col", "full_name");
	td.textContent = escText(m.full_name);
	tr.appendChild(td);

	// 3: gender_display
	td = document.createElement("td");
	td.setAttribute("data-col", "gender_display");
	td.textContent = escText(m.gender_display);
	tr.appendChild(td);

	// 4: phone_number (format như filter)
	td = document.createElement("td");
	td.setAttribute("data-col", "phone_number");
	td.textContent = escText(formatVnPhone(m.phone_number));
	tr.appendChild(td);

	// 5: id_card
	td = document.createElement("td");
	td.setAttribute("data-col", "id_card");
	td.textContent = escText(m.id_card);
	tr.appendChild(td);

	// 6: permanent_address_display
	td = document.createElement("td");
	td.setAttribute("data-col", "permanent_address_display");
	td.textContent = escText(m.permanent_address_display);
	tr.appendChild(td);

	// 7: income (định dạng VND)
	td = document.createElement("td");
	td.setAttribute("data-col", "income");
	td.textContent = escText(formatVnCurrency(m.income, "VND"));
	tr.appendChild(td);

	// 8: loan_amount (định dạng VND)
	td = document.createElement("td");
	td.setAttribute("data-col", "loan_amount");
	td.textContent = escText(formatVnCurrency(m.loan_amount, "VND"));
	tr.appendChild(td);

	// 9: created_at (string server đã format)
	td = document.createElement("td");
	td.setAttribute("data-col", "created_at");
	td.textContent = escText(m.created_at || "");
	tr.appendChild(td);

	// 10: PDF cell
	tr.appendChild(buildPdfCellStyled(!!m.has_pdf, m.pdf_download_url || null));

	// 11: Detail cell
	tr.appendChild(buildDetailCell(m.detail_url || null));

	// 12: Edit cell
	tr.appendChild(buildEditCell(m.id));

	return tr;
}

function updateRowStyled(tr, m) {
	const setTxt = (col, val) => {
		const td = tr.querySelector(`[data-col="${col}"]`);
		if (td && val !== undefined) td.textContent = escText(val);
	};

	setTxt("full_name", m.full_name);
	setTxt("gender_display", m.gender_display);
	setTxt("phone_number", formatVnPhone(m.phone_number));
	setTxt("id_card", m.id_card);
	setTxt("permanent_address_display", m.permanent_address_display);
	setTxt("income", formatVnCurrency(m.income, "VND"));
	setTxt("loan_amount", formatVnCurrency(m.loan_amount, "VND"));
	setTxt("created_at", m.created_at || "");

	const oldPdf = tr.querySelector('[data-col="pdf"]');
	const freshPdf = buildPdfCellStyled(!!m.has_pdf, m.pdf_download_url || null);
	if (oldPdf) {
		tr.replaceChild(freshPdf, oldPdf);
	}

	const oldEdit = tr.querySelector('[data-col="edit"]');
	const freshEdit = buildEditCell(m.id);
	if (oldEdit) {
		tr.replaceChild(freshEdit, oldEdit);
	}

	const oldDetail = tr.querySelector('[data-col="detail"]');
	const freshDetail = buildDetailCell(m.detail_url || null);
	if (oldDetail) {
		tr.replaceChild(freshDetail, oldDetail);
	}

	// optional: highlight 1s cho dễ thấy cập nhật
	tr.classList.add("table-warning");
	setTimeout(() => tr.classList.remove("table-warning"), 1200);
}

function updateOrPrependRow(m) {
	const tbody = document.querySelector("table tbody");
	if (!tbody) return;

	// Xoá hàng "Chưa có dữ liệu"
	const empty = tbody.querySelector("td[colspan]");
	if (empty && empty.parentElement) empty.parentElement.remove();

	let tr = tbody.querySelector(`tr[data-id="${m.id}"]`);
	if (tr) {
		updateRowStyled(tr, m);
	} else {
		tr = buildRowStyled(m);
		tbody.prepend(tr);
	}
}
