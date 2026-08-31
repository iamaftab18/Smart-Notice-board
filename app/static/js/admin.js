(function () {
  "use strict";

  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  const els = {
    tbody: document.getElementById("notices-tbody"),
    emptyState: document.getElementById("empty-state"),
    btnNew: document.getElementById("btn-new-notice"),
    modal: document.getElementById("notice-modal"),
    modalTitle: document.getElementById("notice-modal-title"),
    form: document.getElementById("notice-form"),
    formError: document.getElementById("notice-form-error"),
    fieldId: document.getElementById("notice-id"),
    fieldTitle: document.getElementById("notice-title"),
    fieldDate: document.getElementById("notice-date"),
    fieldPriority: document.getElementById("notice-priority"),
    fieldDescription: document.getElementById("notice-description"),
    fieldPublish: document.getElementById("notice-publish"),
    deleteModal: document.getElementById("delete-modal"),
    confirmDeleteBtn: document.getElementById("confirm-delete-btn"),
    toastContainer: document.getElementById("toast-container"),
    statTotal: document.getElementById("stat-total"),
    statPublished: document.getElementById("stat-published"),
    statDrafts: document.getElementById("stat-drafts"),
    statUrgent: document.getElementById("stat-urgent"),
  };

  let pendingDeleteId = null;

  // ---------- helpers ----------

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

  function formatDate(isoDate) {
    const [y, m, d] = isoDate.split("-").map(Number);
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
  }

  function priorityBadge(priority) {
    if (priority === "urgent") {
      return '<span class="inline-flex items-center gap-1 rounded-full bg-red-50 text-red-700 ring-1 ring-red-100 px-2.5 py-1 text-xs font-semibold">Urgent</span>';
    }
    if (priority === "important") {
      return '<span class="inline-flex items-center gap-1 rounded-full bg-amber-50 text-amber-700 ring-1 ring-amber-100 px-2.5 py-1 text-xs font-semibold">Important</span>';
    }
    return '<span class="inline-flex items-center gap-1 rounded-full bg-slate-100 text-slate-600 ring-1 ring-slate-200 px-2.5 py-1 text-xs font-semibold">Normal</span>';
  }

  function statusBadge(isPublished) {
    if (isPublished) {
      return '<span class="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100 px-2.5 py-1 text-xs font-semibold"><span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span> Published</span>';
    }
    return '<span class="inline-flex items-center gap-1.5 rounded-full bg-slate-100 text-slate-500 ring-1 ring-slate-200 px-2.5 py-1 text-xs font-semibold"><span class="h-1.5 w-1.5 rounded-full bg-slate-400"></span> Draft</span>';
  }

  function rowHtml(notice) {
    const toggleClasses = notice.is_published
      ? "bg-white ring-slate-300 text-slate-600 hover:bg-slate-50"
      : "bg-brand-600 ring-brand-600 text-white hover:bg-brand-700";
    return `
      <td class="px-5 py-4 max-w-sm">
        <p class="font-semibold text-slate-900 truncate">${escapeHtml(notice.title)}</p>
        <p class="text-sm text-slate-500 truncate">${escapeHtml(notice.description)}</p>
      </td>
      <td class="px-5 py-4 text-sm text-slate-600 whitespace-nowrap">${formatDate(notice.notice_date)}</td>
      <td class="px-5 py-4">${priorityBadge(notice.priority)}</td>
      <td class="px-5 py-4">${statusBadge(notice.is_published)}</td>
      <td class="px-5 py-4">
        <div class="flex items-center justify-end gap-2">
          <button data-action="toggle" data-id="${notice.id}" data-published="${notice.is_published}"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold ring-1 transition ${toggleClasses}">
            ${notice.is_published ? "Unpublish" : "Publish"}
          </button>
          <button data-action="announce" data-id="${notice.id}"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold ring-1 ring-slate-300 text-slate-600 hover:bg-slate-50 transition">
            🔊 Announce
          </button>
          <button data-action="edit" data-id="${notice.id}"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold ring-1 ring-slate-300 text-slate-600 hover:bg-slate-50 transition">
            Edit
          </button>
          <button data-action="delete" data-id="${notice.id}"
                  class="rounded-lg px-3 py-1.5 text-xs font-semibold ring-1 ring-red-200 text-red-600 hover:bg-red-50 transition">
            Delete
          </button>
        </div>
      </td>`;
  }

  function upsertRow(notice) {
    let row = els.tbody.querySelector(`tr[data-notice-row="${notice.id}"]`);
    if (!row) {
      row = document.createElement("tr");
      row.setAttribute("data-notice-row", notice.id);
      row.className = "hover:bg-slate-50/70 transition";
      els.tbody.prepend(row);
    }
    row.innerHTML = rowHtml(notice);
    updateStats();
    els.emptyState.classList.toggle("hidden", els.tbody.children.length > 0);
  }

  function removeRow(id) {
    const row = els.tbody.querySelector(`tr[data-notice-row="${id}"]`);
    if (row) row.remove();
    updateStats();
    els.emptyState.classList.toggle("hidden", els.tbody.children.length > 0);
  }

  function updateStats() {
    const rows = Array.from(els.tbody.querySelectorAll("tr[data-notice-row]"));
    const total = rows.length;
    let published = 0;
    rows.forEach((row) => {
      const btn = row.querySelector('[data-action="toggle"]');
      if (btn && btn.dataset.published === "true") published += 1;
    });
    const urgent = rows.filter((row) => row.querySelector(".bg-red-50")).length;
    els.statTotal.textContent = total;
    els.statPublished.textContent = published;
    els.statDrafts.textContent = total - published;
    els.statUrgent.textContent = urgent;
  }

  // ---------- modal open/close ----------

  function openNoticeModal(mode, notice) {
    els.form.reset();
    els.formError.classList.add("hidden");
    if (mode === "edit" && notice) {
      els.modalTitle.textContent = "Edit notice";
      els.fieldId.value = notice.id;
      els.fieldTitle.value = notice.title;
      els.fieldDate.value = notice.notice_date;
      els.fieldPriority.value = notice.priority;
      els.fieldDescription.value = notice.description;
      els.fieldPublish.checked = !!notice.is_published;
      els.fieldPublish.parentElement.classList.add("hidden"); // publishing is handled via the table toggle when editing
    } else {
      els.modalTitle.textContent = "New notice";
      els.fieldId.value = "";
      els.fieldDate.valueAsDate = new Date();
      els.fieldPriority.value = "normal";
      els.fieldPublish.checked = false;
      els.fieldPublish.parentElement.classList.remove("hidden");
    }
    els.modal.classList.remove("hidden");
    els.fieldTitle.focus();
  }

  function closeNoticeModal() {
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

  // ---------- event wiring ----------

  els.btnNew.addEventListener("click", () => openNoticeModal("create"));

  document.querySelectorAll("[data-modal-close], [data-modal-backdrop]").forEach((el) => {
    el.addEventListener("click", closeNoticeModal);
  });
  document.querySelectorAll("[data-delete-cancel], [data-delete-backdrop]").forEach((el) => {
    el.addEventListener("click", closeDeleteModal);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeNoticeModal();
      closeDeleteModal();
    }
  });

  els.tbody.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const id = btn.dataset.id;
    const action = btn.dataset.action;

    if (action === "edit") {
      apiFetch(`/admin/notices/${id}`)
        .then((data) => openNoticeModal("edit", data.notice))
        .catch((err) => showToast(err.message, "error"));
    } else if (action === "announce") {
      btn.disabled = true;
      apiFetch(`/admin/notices/${id}/announce`, { method: "POST" })
        .then(() => showToast("Announcing on the connected speaker…"))
        .catch((err) => showToast(err.message, "error"))
        .finally(() => {
          btn.disabled = false;
        });
    } else if (action === "delete") {
      openDeleteModal(id);
    } else if (action === "toggle") {
      const isPublished = btn.dataset.published === "true";
      const endpoint = isPublished ? "unpublish" : "publish";
      btn.disabled = true;
      apiFetch(`/admin/notices/${id}/${endpoint}`, { method: "POST" })
        .then((data) => {
          upsertRow(data.notice);
          showToast(isPublished ? "Notice unpublished." : "Notice published to the board.");
        })
        .catch((err) => showToast(err.message, "error"))
        .finally(() => {
          btn.disabled = false;
        });
    }
  });

  els.confirmDeleteBtn.addEventListener("click", () => {
    if (!pendingDeleteId) return;
    const id = pendingDeleteId;
    els.confirmDeleteBtn.disabled = true;
    apiFetch(`/admin/notices/${id}`, { method: "DELETE" })
      .then(() => {
        removeRow(id);
        showToast("Notice deleted.");
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

    const id = els.fieldId.value;
    const payload = {
      title: els.fieldTitle.value.trim(),
      notice_date: els.fieldDate.value,
      priority: els.fieldPriority.value,
      description: els.fieldDescription.value.trim(),
    };

    const submitBtn = els.form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    const request = id
      ? apiFetch(`/admin/notices/${id}`, { method: "PUT", body: JSON.stringify(payload) })
      : apiFetch("/admin/notices", { method: "POST", body: JSON.stringify(payload) });

    request
      .then((data) => {
        let notice = data.notice;
        if (!id && els.fieldPublish.checked) {
          return apiFetch(`/admin/notices/${notice.id}/publish`, { method: "POST" }).then((d) => d.notice);
        }
        return notice;
      })
      .then((notice) => {
        upsertRow(notice);
        closeNoticeModal();
        showToast(id ? "Notice updated." : "Notice created.");
      })
      .catch((err) => {
        els.formError.textContent = err.message;
        els.formError.classList.remove("hidden");
      })
      .finally(() => {
        submitBtn.disabled = false;
      });
  });

  updateStats();
})();
