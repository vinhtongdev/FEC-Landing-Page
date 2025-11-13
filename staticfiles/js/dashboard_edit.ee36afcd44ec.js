// static/js/dashboard_edit.js
(function () {
    function getCookie(name) {
        const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
        return m ? m.pop() : "";
    }
    const csrftoken = getCookie("csrftoken");

    const editModalEl = document.getElementById("editModal");
    const editModal = new bootstrap.Modal(editModalEl, { backdrop: "static" });
    const editContent = document.getElementById("editModalContent");

    const approveModalEl = document.getElementById("approveModal");
    const approveModal = new bootstrap.Modal(approveModalEl, {
        backdrop: "static",
    });
    const approveAlerts = document.getElementById("approve-alerts");
    const approveCodeInput = document.getElementById("approve-code");
    const btnApproveVerify = document.getElementById("btn-approve-verify");

    let currentApprovalId = null;
    let currentSaveUrl = null;

    function showAlert(container, kind, msg) {
        if (!container) return;
        container.innerHTML = `
            <div class="alert alert-${kind} alert-dismissible fade show" role="alert">
                ${msg}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>`;
    }

    // Mở modal edit (chỉ trigger từ button có class .btn-edit và data-id)
    document.body.addEventListener("click", async function (e) {
        const btn = e.target.closest(".btn-edit");
        if (!btn) return;

        const id = btn.getAttribute("data-id");
        if (!id) {
            console.error("Button .btn-edit thiếu data-id"); // Log lỗi để debug
            return;
        }

        const url = `/dashboard/customer/${id}/edit/`;

        const resp = await fetch(url, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const html = await resp.text();
        editContent.innerHTML = html;

        // Lưu reference tới action (sửa: dùng form.action thay vì data-action)
        const form = editContent.querySelector("#edit-form");
        currentSaveUrl = form ? form.action : null; // Hoặc form.getAttribute("action")

        // Gắn handler nút Save trong modal này
        const btnSave = editContent.querySelector("#btn-save-customer");
        if (btnSave) {
            btnSave.addEventListener("click", onSaveClick, { once: true });
        } else {
            console.error("Không tìm thấy #btn-save-customer"); // Log nếu thiếu ID
        }

        editModal.show();
    });

    async function onSaveClick() {
        if (!currentSaveUrl) {
            alert("Không tìm thấy URL lưu dữ liệu.");
            return;
        }

        const form = editContent.querySelector("#edit-form");
        const formData = new FormData(form);

        const resp = await fetch(currentSaveUrl, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrftoken,
            },
            body: formData,
        });

        if (resp.status === 400) {
            // lỗi form, render lại trường
            const data = await resp.json();
            const fieldsBox = editContent.querySelector("#edit-form-fields");
            if (fieldsBox && data.errors_html)
                fieldsBox.innerHTML = data.errors_html;
            // Cho phép bấm Save tiếp:
            const btnSave = editContent.querySelector("#btn-save-customer");
            if (btnSave)
                btnSave.addEventListener("click", onSaveClick, { once: true });
            return;
        }

        const data = await resp.json();

        if (data.ok) {
            // Lưu trực tiếp (manager hoặc không có thay đổi)
            editModal.hide();
            location.reload();
            return;
        }

        if (data.requires_approval) {
            // Staff → cần mã 6 số
            currentApprovalId = data.approval_id;
            editModal.hide();
            approveAlerts.innerHTML = "";
            approveCodeInput.value = "";
            approveModal.show();
            return;
        }

        // fallback
        alert(data.message || "Không thể lưu.");
    }

    btnApproveVerify.addEventListener("click", async function () {
        if (!currentApprovalId) return;
        const code = (approveCodeInput.value || "").trim();
        if (code.length !== 6) {
            showAlert(approveAlerts, "warning", "Vui lòng nhập đủ 6 số.");
            return;
        }
        const url = `/dashboard/approval/${currentApprovalId}/verify/`;
        const resp = await fetch(url, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrftoken,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            body: new URLSearchParams({ code }),
        });
        if (!resp.ok){
            const text = await resp.text();
            console.error('Verify failed', resp.status, text)
            alert(`Lỗi xác minh (${resp.status}). Kiểm tra log server.`)
            return;
        }
        let data;
        try{
            data = await resp.json();
        } catch(e) {
            const text = await resp.text();
            console.error('Response không phải JSON:', text);
            alert('Phản hồi không phải JSON.');
            return;
        }     
        
        if (data.ok) {
            approveModal.hide();
            location.reload();
        } else {
            showAlert(approveAlerts, "danger", data.message || "Mã không đúng.");
        }
    });
})();