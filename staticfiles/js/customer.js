(function () {
	const fmt = new Intl.NumberFormat("vi-VN");
	const STEP_DEFAULT = 1_000_000;

	const $ = (sel) => document.querySelector(sel);
	const toNumber = (v) => {
		if (v == null) return 0;
		const n = String(v).replace(/[^\d]/g, ""); // Loại bỏ tất cả ký tự không phải số
		return n === "" ? 0 : parseInt(n, 10);
	};
	const clamp = (x, min, max) => Math.min(Math.max(x, min), max);
	const isEmpty = (input) => !input.value || String(input.value).trim() === "";

	const formatInput = (input) => {
		const n = toNumber(input.value);
		input.value = n ? fmt.format(n) : "";
	};

	const setValue = (input, newVal, { forceZeroDisplay = false } = {}) => {
		const min = toNumber(input.dataset.min) || 0;
		const max = toNumber(input.dataset.max) || 1_000_000_000;
		const clamped = clamp(newVal, min, max);

		if (clamped === 0 && forceZeroDisplay) {
			input.value = "0";
		} else {
			input.value = clamped ? fmt.format(clamped) : "";
		}
		hideRequired(input);
		validateStep(input);
		updateButtonsFor(input);
		validateRanges();
	};

	const bump = (input, sign = +1) => {
		const val = toNumber(input.value);
		const step = toNumber(input.dataset.step) || STEP_DEFAULT;
		const next = val + sign * step;
		setValue(input, next, { forceZeroDisplay: true });
		input.dataset.touched = "1";
	};

	// ====== HELPERS: show/hide ======
	function idBase(input) {
		return input.id;
	}
	function elRequired(input) {
		return $(`#${idBase(input)}_required`);
	}
	function elStep(input) {
		return $(`#${idBase(input)}_step`);
	}

	function show(el, on) {
		if (el) el.classList.toggle("d-none", !on);
	}
	function showRequired(input) {
		show(elRequired(input), true);
	}
	function hideRequired(input) {
		show(elRequired(input), false);
	}
	function showStep(input) {
		show(elStep(input), true);
	}
	function hideStep(input) {
		show(elStep(input), false);
	}

	function validateStep(input) {
		const step = toNumber(input.dataset.step) || STEP_DEFAULT;
		const val = toNumber(input.value);
		if (val > 0 && val % step !== 0) showStep(input);
		else hideStep(input);
	}

	// ==== Validate theo khoảng (3 dòng help đỏ giống hình) ====
	function validateRanges() {
		const loan = $("#loan_amount");
		const inc = $("#income");
		const mon = $("#monthly_payment");
		const loanV = toNumber(loan?.value);
		const incV = toNumber(inc?.value);
		const monV = toNumber(mon?.value);

		// Vay 10–100 triệu: chỉ hiện khi >0 mà ngoài khoảng
		show(
			$("#loan_amount_help"),
			loanV > 0 && !(loanV >= 10_000_000 && loanV <= 100_000_000)
		);

		// Thu nhập 3–100 triệu
		show(
			$("#income_help"),
			incV > 0 && !(incV >= 3_000_000 && incV <= 100_000_000)
		);

		// Trả góp ≤ 50% thu nhập (chỉ khi đã có income)
		const over50 = incV > 0 && monV > Math.floor(incV * 0.5);
		show($("#monthly_payment_help"), over50);
	}

	// ====== GÁN SỰ KIỆN NÚT +/- ======
	document.querySelectorAll(".money-inc,.money-dec").forEach((btn) => {
		btn.addEventListener("click", () => {
			const sel = btn.getAttribute("data-target");
			const input = document.querySelector(sel);
			if (!input) return;

			if (
				btn.classList.contains("money-dec") &&
				isEmpty(input) &&
				input.dataset.touched !== "1"
			) {
				showRequired(input); // mới load, rỗng → báo required
				return;
			}

			bump(input, btn.classList.contains("money-inc") ? +1 : -1);
			input.dispatchEvent(new Event("change", { bubbles: true }));
		});
	});

	// ====== SỰ KIỆN TRÊN INPUT ======
	document.querySelectorAll(".money-input").forEach((inp) => {
		updateButtonsFor(inp);

		inp.addEventListener("input", () => {
			const raw = inp.value;
			const cleaned = raw.replace(/[^\d]/g, ""); // Chỉ giữ số
			if (raw !== cleaned) inp.value = cleaned;
			hideRequired(inp);
			validateRanges();
		});

		inp.addEventListener("blur", () => {
			if (isEmpty(inp)) {
				validateRanges();
				return;
			}
			formatInput(inp); // Định dạng khi mất focus
			validateRanges();
		});

		inp.addEventListener("change", () => {
			if (inp.dataset.touched === "1" && isEmpty(inp)) {
				setValue(inp, 0, { forceZeroDisplay: true });
				return;
			}
			const min = toNumber(inp.dataset.min) || 0;
			const max = toNumber(inp.dataset.max) || 1_000_000_000;
			let n = toNumber(inp.value);
			n = clamp(n, min, max);
			inp.value = n ? fmt.format(n) : ""; // Định dạng hiển thị
			validateStep(inp);
			updateButtonsFor(inp);
			validateRanges();
		});

		// Loại bỏ định dạng khi submit form
		const form = inp.closest("form");
		if (form) {
			form.addEventListener("submit", () => {
				const n = toNumber(inp.value);
				inp.value = n.toString(); // Gửi giá trị số nguyên không định dạng
			});
		}
	});

	// ====== BUTTON STATE ======
	function updateButtonsFor(input) {
		const sel = `#${input.id}`;
		const dec = document.querySelector(`.money-dec[data-target="${sel}"]`);
		const inc = document.querySelector(`.money-inc[data-target="${sel}"]`);
		const min = toNumber(input.dataset.min) || 0;
		const max = toNumber(input.dataset.max) || 1_000_000_000;
		const val = toNumber(input.value);

		if (dec)
			dec.disabled =
				(!isEmpty(input) && val <= min) ||
				(isEmpty(input) && input.dataset.touched === "1");
		if (isEmpty(input) && input.dataset.touched !== "1" && dec)
			dec.disabled = false;
		if (inc) inc.disabled = !isEmpty(input) && val >= max;
	}

	// Khởi tạo validate khi tải trang
	validateRanges();
})();

document.addEventListener("DOMContentLoaded", function () {
	flatpickr("#id_birth_date", {
		dateFormat: "d/m/Y",
		allowInput: true,
		locale: "vn",
	});
});
