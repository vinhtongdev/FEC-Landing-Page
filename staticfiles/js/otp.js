
(function () {
	// ===== Đếm ngược cho nút "Gửi lại" =====
	const btn = document.getElementById("btn-resend");
	const cd = document.getElementById("countdown");

	function startCountdown(initial) {
		if (!btn || !cd) return;
		let left = parseInt(initial, 10);
		if (isNaN(left) || left < 0) left = 0;

		function tick() {
			if (left <= 0) {
				cd.textContent = "0";
				btn.disabled = false;
				btn.textContent = "Gửi lại";
				return;
			}
			cd.textContent = String(left);
			left -= 1;
			setTimeout(tick, 1000);
		}

		if (left > 0) {
			btn.disabled = true;
			tick();
		} else {
			btn.disabled = false;
			btn.textContent = "Gửi lại";
		}
	}

	if (btn && cd) {
		startCountdown(cd.textContent || "0");
	}

	// ===== Modal progress khi nhấn "Gửi lại" =====
	const resendBtn = document.getElementById("btn-resend");
	const bar = document.getElementById("resendBar");
	const modalEl = document.getElementById("resendModal");
	const modal = modalEl
		? new bootstrap.Modal(modalEl, { backdrop: "static", keyboard: false })
		: null;

	let timer = null;
	function runBar() {
		if (!bar) return;
		let p = 15;
		bar.style.width = p + "%";
		bar.textContent = p + "%";
		timer = setInterval(() => {
			if (p < 90) {
				p += Math.max(1, Math.round((90 - p) / 8));
				bar.style.width = p + "%";
				bar.textContent = p + "%";
			}
		}, 200);
	}
	function stopBar() {
		if (!bar) return;
		if (timer) clearInterval(timer);
		timer = null;
		bar.style.width = "100%";
		bar.textContent = "100%";
	}

	if (resendBtn && modal) {
		resendBtn.addEventListener("click", function () {
			if (resendBtn.disabled) return; // còn countdown
			modal.show();
			runBar();
			// Khi trang điều hướng (server phản hồi), dừng progress
			window.addEventListener("beforeunload", stopBar, { once: true });
		});
	}
})();
