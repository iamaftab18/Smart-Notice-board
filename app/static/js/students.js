(function () {
  "use strict";

  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  const els = {
    tbody: document.getElementById("students-tbody"),
    emptyState: document.getElementById("empty-state"),
    btnNew: document.getElementById("btn-new-student"),
    modal: document.getElementById("student-modal"),
    form: document.getElementById("student-form"),
    formError: document.getElementById("student-form-error"),
    fieldName: document.getElementById("student-name"),
    fieldEnrollment: document.getElementById("student-enrollment"),
    fieldEmail: document.getElementById("student-email"),
    deleteModal: document.getElementById("delete-modal"),
    confirmDeleteBtn: document.getElementById("confirm-delete-btn"),
    toastContainer: document.getElementById("toast-container"),
  };

  let pendingDeleteId = null;

  function apiFetch(url, options = {}) {
    const opts = Object.assign({}, options);
    opts.headers = Object.assign(
      { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
      options.headers || {}
    );
    return fetch(url, opts).then(async (res) => {
      let body = null;
      try {
        body = await res.json();
      } catch (e) {
        body = null;
      }
      if (!res.ok || !body || body.ok === false) {
        const message = (body && body.error) || "Something went wrong. Please try again.";
        throw new Error(message);
      }
      return body;
    });
  }

  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    const palette =
      type === "success"
        ? "bg-emerald-600"
        : type === "error"
        ? "bg-red-600"
        : "bg-slate-800";
    toast.className = `${palette} text-white text-sm font-medium px-4 py-3 rounded-lg shadow-xl animate-fade-in max-w-xs`;
    toast.textContent = message;
    els.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = "opacity .3s ease";
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function rowHtml(student) {
    return `
      <td class="px-5 py-4 font-semibold text-slate-900">${escapeHtml(student.name)}</td>
      <td class="px-5 py-4 text-sm text-slate-600">${escapeHtml(student.enrollment_no)}</td>
      <td class="px-5 py-4 text-sm text-slate-600">${escapeHtml(student.email)}</td>
      <td class="px-5 py-4">
        <div class="flex items-center justify-end gap-2">
          <button data-action="delete" data-id="${student.id}"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold ring-1 ring-red-200 text-red-600 hover:bg-red-50 transition">
            Remove
          </button>
        </div>
      </td>`;
  }

  function addRow(student) {
    const row = document.createElement("tr");
    row.setAttribute("data-student-row", student.id);
    row.className = "hover:bg-slate-50/70 transition";
    row.innerHTML = rowHtml(student);
    els.tbody.prepend(row);
    els.emptyState.classList.add("hidden");
  }

  function removeRow(id) {
    const row = els.tbody.querySelector(`tr[data-student-row="${id}"]`);
    if (row) row.remove();
    els.emptyState.classList.toggle("hidden", els.tbody.children.length > 0);
  }

  function openModal() {
    els.form.reset();
    els.formError.classList.add("hidden");
    els.modal.classList.remove("hidden");
    els.fieldName.focus();
  }

  function closeModal() {
    els.modal.classList.add("hidden");
  }

  function openDeleteModal(id) {
    pendingDeleteId = id;
    els.deleteModal.classList.remove("hidden");
  }

  function closeDeleteModal() {
    pendingDeleteId = null;
    els.deleteModal.classList.add("hidden");
  }

  els.btnNew.addEventListener("click", openModal);

  document.querySelectorAll("[data-modal-close], [data-modal-backdrop]").forEach((el) => {
    el.addEventListener("click", closeModal);
  });
  document.querySelectorAll("[data-delete-cancel], [data-delete-backdrop]").forEach((el) => {
    el.addEventListener("click", closeDeleteModal);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal();
      closeDeleteModal();
    }
  });

  els.tbody.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    if (btn.dataset.action === "delete") {
      openDeleteModal(btn.dataset.id);
    }
  });

  els.confirmDeleteBtn.addEventListener("click", () => {
    if (!pendingDeleteId) return;
    const id = pendingDeleteId;
    els.confirmDeleteBtn.disabled = true;
    apiFetch(`/admin/students/${id}`, { method: "DELETE" })
      .then(() => {
        removeRow(id);
        showToast("Student removed.");
        closeDeleteModal();
      })
      .catch((err) => showToast(err.message, "error"))
      .finally(() => {
        els.confirmDeleteBtn.disabled = false;
      });
  });

  els.form.addEventListener("submit", (e) => {
    e.preventDefault();
    els.formError.classList.add("hidden");

    const payload = {
      name: els.fieldName.value.trim(),
      enrollment_no: els.fieldEnrollment.value.trim(),
      email: els.fieldEmail.value.trim(),
    };

    const submitBtn = els.form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    apiFetch("/admin/students", { method: "POST", body: JSON.stringify(payload) })
      .then((data) => {
        addRow(data.student);
        closeModal();
        showToast("Student added.");
      })
      .catch((err) => {
        els.formError.textContent = err.message;
        els.formError.classList.remove("hidden");
      })
      .finally(() => {
        submitBtn.disabled = false;
      });
  });
})();
