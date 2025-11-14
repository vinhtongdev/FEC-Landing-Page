// static/js/otp.js
(function () {
	const btn = document.getElementById("btn-resend");
	const form = document.getElementById("otp-form");
	const cd = document.getElementById("countdown");
	const wrap = document.getElementById("countdown-wrap");
	const alertsBox = document.getElementById("otp-alerts");
	if (!btn || !form || !cd || !wrap) return;

	// ------ COUNTDOWN ------
	let countdownTid = null;

	function setState(left) {
		// left: số giây còn lại
		if (left > 0) {
			cd.textContent = String(left);
			wrap.style.display = ""; // hiện "(Xs)"
			btn.disabled = true;
		} else {
			cd.textContent = "0";
			wrap.style.display = "none"; // ẩn "(Xs)"
			btn.disabled = false;
		}
	}

	function startCountdown(sec) {
		if (countdownTid) {
			clearTimeout(countdownTid);
			countdownTid = null;
		}
		let left = parseInt(sec, 10);
		if (isNaN(left) || left < 0) left = 0;

		function tick() {
			setState(left);
			if (left <= 0) return;
			left -= 1;
			countdownTid = setTimeout(tick, 1000);
		}
		tick();
	}

	// Khởi động theo giá trị server render
	startCountdown(parseInt(cd.textContent || "0", 10));

	// ------ PROGRESS MODAL ------
	const modalEl = document.getElementById("resendModal");
	const modal = modalEl
		? new bootstrap.Modal(modalEl, { backdrop: "static", keyboard: false })
		: null;
	const bar = document.getElementById("resendBar");
	let progressTid = null;

	function startProgress() {
		if (!modal || !bar) return;
		bar.style.width = "10%";
		bar.textContent = "10%";
		modal.show();
		let p = 10;
		progressTid = setInterval(() => {
			if (p < 90) {
				p = Math.min(90, p + Math.max(1, Math.round((90 - p) / 6)));
				bar.style.width = p + "%";
				bar.textContent = p + "%";
			}
		}, 180);
	}

	function stopProgress(done = true) {
		if (!modal || !bar) return;
		if (progressTid) {
			clearInterval(progressTid);
			progressTid = null;
		}
		// Tránh cảnh báo aria-hidden: bỏ focus trước khi ẩn modal
		if (document.activeElement) document.activeElement.blur();
		if (done) {
			bar.style.width = "100%";
			bar.textContent = "100%";
			setTimeout(() => {
				modal.hide();
				btn.focus();
			}, 250);
		} else {
			modal.hide();
			btn.focus();
		}
	}

	if (modalEl) {
		modalEl.addEventListener("hidden.bs.modal", () => {
			btn.focus();
		});
	}

	// ------ ALERT ------
	function showAlert(kind, msg) {
		if (!alertsBox) return;
		alertsBox.innerHTML = `
      <div class="alert alert-${kind} alert-dismissible fade show" role="alert">
        ${msg}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>`;
	}

	// ------ CSRF ------
	function getCookie(name) {
		const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
		return m ? m.pop() : "";
	}
	const csrftoken = getCookie("csrftoken");

	// ------ RESEND via AJAX ------
	btn.addEventListener("click", async function (e) {
		if (btn.disabled) return; // đang cooldown
		e.preventDefault(); // chặn submit đồng bộ

		startProgress();

		try {
			const resp = await fetch(window.location.href, {
				method: "POST",
				headers: {
					"X-Requested-With": "XMLHttpRequest",
					"X-CSRFToken": csrftoken,
					Accept: "application/json",
					"Content-Type":
						"application/x-www-form-urlencoded;charset=UTF-8",
				},
				body: new URLSearchParams({
					csrfmiddlewaretoken: csrftoken,
					action: "resend",
				}),
			});

			const data = await resp.json().catch(() => ({}));
			stopProgress(true);

			// Server nên trả TTL mới (vd 60s): {'ok': True, 'remaining': 60, ...}
			if (typeof data.remaining === "number") {
				startCountdown(data.remaining); // << reset & chạy lại
			}

			if (data.ok) {
				showAlert("success", data.message || "Đã gửi lại OTP.");
			} else {
				showAlert("warning", data.message || "Không thể gửi lại OTP.");
			}
		} catch (err) {
			stopProgress(false);
			showAlert("danger", "Lỗi kết nối. Vui lòng thử lại.");
		}
	});
})();
