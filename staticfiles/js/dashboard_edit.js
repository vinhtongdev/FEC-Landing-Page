// static/js/dashboard_edit.js

document.addEventListener("DOMContentLoaded", () => {
	// --- MODALS ---
	const editModalEl = document.getElementById("editModal");
	const editModal = editModalEl ? new bootstrap.Modal(editModalEl) : null;
	const editModalContent = document.getElementById("editModalContent");

	const approveModalEl = document.getElementById("approveModal");
	const approveModal = approveModalEl
		? new bootstrap.Modal(approveModalEl)
		: null;
	const approveCodeInput = document.getElementById("approve-code");
	const approveVerifyBtn = document.getElementById("btn-approve-verify");
	const approveAlerts = document.getElementById("approve-alerts");

	// --- MAIN ALERTS ---
	const mainAlertsContainer = document.getElementById("main-alerts");

	// --- STATE ---
	let currentApprovalId = null;

	if (!editModal || !approveModal || !editModalContent) {
		console.error("Một hoặc nhiều thành phần modal không tồn tại.");
		return;
	}

	// --- HELPER: Show main alert ---
	function showMainAlert(type, message, duration = 5000) {
		if (!mainAlertsContainer) return;

		const wrapper = document.createElement("div");
		wrapper.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
		mainAlertsContainer.append(wrapper);

		if (duration) {
			setTimeout(() => {
				const alert = bootstrap.Alert.getOrCreateInstance(
					wrapper.firstChild
				);
				if (alert) {
					alert.close();
				}
			}, duration);
		}
	}

	// --- HELPER: Show alert inside approve modal ---
	function showApproveAlert(type, message) {
		if (!approveAlerts) return;
		approveAlerts.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
	}

	// --- 1. Mở modal chỉnh sửa ---
	document.body.addEventListener("click", async (e) => {
		if (!e.target.matches(".btn-edit")) return;

		const customerId = e.target.dataset.id;
		if (!customerId) return;

		try {
			const url = `/management/customer/${customerId}/edit/`;
			const response = await fetch(url);
			if (!response.ok) throw new Error("Không thể tải form chỉnh sửa.");

			editModalContent.innerHTML = await response.text();
			editModal.show();
		} catch (error) {
			showMainAlert("danger", error.message);
		}
	});

	// --- 2. Submit form chỉnh sửa (bên trong modal) ---
	editModalContent.addEventListener("submit", async (e) => {
		if (!e.target.matches("form")) return;
		e.preventDefault();

		const form = e.target;
		const url = form.action;
		const formData = new FormData(form);

		try {
			const response = await fetch(url, {
				method: "POST",
				body: formData,
				headers: { "X-Requested-With": "XMLHttpRequest" },
			});

			const data = await response.json();

			if (response.ok) {
				// Manager tự sửa -> thành công
				editModal.hide();
				showMainAlert("success", data.message || "Cập nhật thành công!");
				// WebSocket sẽ tự cập nhật table row
			} else if (response.status === 202 && data.requires_approval) {
				// Staff sửa -> cần approval
				currentApprovalId = data.approval_id;
				editModal.hide();
				approveModal.show();
			} else if (response.status === 400) {
				// Lỗi validation
				const errorsContainer = form.querySelector(".form-errors");
				if (errorsContainer && data.errors_html) {
					errorsContainer.innerHTML = data.errors_html;
				}
			} else {
				throw new Error(data.message || "Lỗi không xác định.");
			}
		} catch (error) {
			showMainAlert("danger", `Lỗi khi lưu: ${error.message}`);
		}
	});

	// --- 3. Xử lý modal nhập mã xác thực ---
	approveModalEl.addEventListener("shown.bs.modal", () => {
		approveCodeInput.value = "";
		approveCodeInput.focus();
		approveAlerts.innerHTML = "";
	});

	approveVerifyBtn.addEventListener("click", async () => {
		const code = approveCodeInput.value.trim();
		if (!code || !currentApprovalId) return;

		// Vô hiệu hóa nút để tránh click nhiều lần
		approveVerifyBtn.disabled = true;
		approveVerifyBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Đang xử lý...
        `;

		try {
			// Lấy URL từ biến global đã gán trong template
			const url = window.APPROVAL_VERIFY_URL_TPL.replace(
				"/0/",
				`/${currentApprovalId}/`
			);
			const csrftoken = document.querySelector(
				"[name=csrfmiddlewaretoken]"
			).value;

			const response = await fetch(url, {
				method: "POST",
				body: new URLSearchParams({ code, csrfmiddlewaretoken: csrftoken }),
				headers: { "X-Requested-With": "XMLHttpRequest" },
			});

			const data = await response.json();

			if (response.ok && data.ok) {
				approveModal.hide();
				showMainAlert("success", data.message); // <-- Hiển thị thông báo thành công ở trang chính
				// WebSocket sẽ tự cập nhật table row
			} else {
				// Hiển thị lỗi ngay trong modal
				showApproveAlert("danger", data.message || "Lỗi không xác định.");
			}
		} catch (error) {
			showApproveAlert("danger", `Lỗi kết nối: ${error.message}`);
		} finally {
			// Khôi phục lại nút
			approveVerifyBtn.disabled = false;
			approveVerifyBtn.textContent = "Xác nhận";
			currentApprovalId = null; // Reset
		}
	});
});
