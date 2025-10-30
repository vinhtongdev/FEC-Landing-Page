// static/js/sign.js
(function () {
	const canvas = document.getElementById("signature");
	if (!canvas) return;

	// SignaturePad (UMD) đã được load từ CDN trong template
	const pad = new SignaturePad(canvas, {
		backgroundColor: "rgba(255,255,255,1)",
	});

	// Resize cho HiDPI + responsive
	function resizeCanvas() {
		const ratio = Math.max(window.devicePixelRatio || 1, 1);
		const displayWidth = canvas.clientWidth;
		const displayHeight = canvas.clientHeight;
		canvas.width = displayWidth * ratio;
		canvas.height = displayHeight * ratio;
		const ctx = canvas.getContext("2d");
		ctx.scale(ratio, ratio);
		// Không clear chữ ký khi resize nếu muốn giữ nét; ở đây clear để tránh méo
		pad.clear();
	}
	window.addEventListener("resize", resizeCanvas);
	resizeCanvas();

	// Nút xóa
	const btnClear = document.getElementById("clear-signature");
	if (btnClear) {
		btnClear.addEventListener("click", function () {
			pad.clear();
		});
	}

	// Submit
	const form = document.getElementById("sign-form");
	const hidden = document.getElementById("signature_data");

	if (form && hidden) {
		form.addEventListener("submit", function (e) {
			if (pad.isEmpty()) {
				e.preventDefault();
				alert("Vui lòng ký trước khi gửi.");
				return;
			}
			hidden.value = pad.toDataURL("image/png");
		});
	}
})();
