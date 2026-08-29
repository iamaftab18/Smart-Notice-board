(function () {
  "use strict";

  const cfg = window.BOARD_CONFIG;
  const noticeArea = document.getElementById("notice-area");
  const dotsEl = document.getElementById("board-dots");
  const clockEl = document.getElementById("board-clock");
  const dateEl = document.getElementById("board-date");
  const rootEl = document.getElementById("board-root");

  let notices = [];
  let signature = "";
  let activeIndex = 0;
  let rotateTimer = null;

  // ---------- clock ----------

  function tickClock() {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
    dateEl.textContent = now.toLocaleDateString("en-US", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }
  tickClock();
  setInterval(tickClock, 1000 * 15);

  // ---------- rendering ----------

  const PRIORITY_THEME = {
    urgent: {
      bg: "from-red-800 via-red-900 to-slate-950",
      badge: "bg-red-600 text-white",
      label: "Urgent",
      accent: "border-red-500",
    },
    important: {
      bg: "from-amber-700 via-amber-900 to-slate-950",
      badge: "bg-amber-500 text-slate-900",
      label: "Important",
      accent: "border-amber-400",
    },
    normal: {
      bg: "from-brand-900 via-brand-950 to-slate-950",
      badge: "bg-brand-500 text-white",
      label: "Notice",
      accent: "border-brand-400",
    },
  };

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function sizeClasses(description) {
    const len = description.length;
    if (len > 900) return { title: "text-4xl sm:text-5xl", body: "text-lg sm:text-xl" };
    if (len > 500) return { title: "text-5xl sm:text-6xl", body: "text-xl sm:text-2xl" };
    if (len > 220) return { title: "text-5xl sm:text-6xl", body: "text-2xl sm:text-3xl" };
    return { title: "text-6xl sm:text-7xl", body: "text-3xl sm:text-4xl" };
  }

  function renderIdle() {
    rootEl.className =
      "h-full w-full relative flex flex-col overflow-hidden bg-gradient-to-br from-brand-900 via-brand-950 to-slate-950 transition-colors duration-700";
    noticeArea.innerHTML = `
      <div class="text-center opacity-90">
        <div class="mx-auto h-24 w-24 rounded-3xl bg-white/10 backdrop-blur flex items-center justify-center ring-1 ring-white/20 mb-8">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 3h6a1 1 0 011 1v1h2a1 1 0 011 1v13a2 2 0 01-2 2H7a2 2 0 01-2-2V6a1 1 0 011-1h2V4a1 1 0 011-1z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 3v3h6V3M9 11h6M9 15h6M9 19h3" />
          </svg>
        </div>
        <p class="font-display font-bold text-4xl sm:text-5xl text-white/90">No notices at the moment</p>
        <p class="text-brand-200/70 text-xl sm:text-2xl mt-3">Please check back later</p>
      </div>`;
    dotsEl.innerHTML = "";
  }

  function renderNotice(notice) {
    const theme = PRIORITY_THEME[notice.priority] || PRIORITY_THEME.normal;
    rootEl.className = `h-full w-full relative flex flex-col overflow-hidden bg-gradient-to-br ${theme.bg} transition-colors duration-700`;

    const sizes = sizeClasses(notice.description);

    noticeArea.innerHTML = `
      <div class="notice-enter w-full max-w-6xl h-full max-h-full flex flex-col bg-white/[0.97] text-slate-900 rounded-3xl shadow-2xl border-t-8 ${theme.accent} p-10 sm:p-14">
        <div class="flex flex-wrap items-center gap-3 mb-6 shrink-0">
          <span class="inline-flex items-center rounded-full ${theme.badge} px-4 py-1.5 text-sm sm:text-base font-bold uppercase tracking-wide">
            ${theme.label}
          </span>
          <span class="inline-flex items-center rounded-full bg-slate-100 text-slate-600 ring-1 ring-slate-200 px-4 py-1.5 text-sm sm:text-base font-semibold">
            ${escapeHtml(notice.notice_date_display)}
          </span>
        </div>
        <h2 class="font-display font-extrabold ${sizes.title} leading-tight mb-6 shrink-0">${escapeHtml(notice.title)}</h2>
        <div class="flex-1 min-h-0 overflow-y-auto pr-2">
          <p class="notice-desc ${sizes.body} leading-relaxed text-slate-700">${escapeHtml(notice.description)}</p>
        </div>
      </div>`;
  }

  function renderDots() {
    if (notices.length <= 1) {
      dotsEl.innerHTML = "";
      return;
    }
    dotsEl.innerHTML = notices
      .map((_, i) => {
        const active = i === activeIndex;
        return `<span class="h-2.5 rounded-full transition-all duration-300 ${
          active ? "w-8 bg-white" : "w-2.5 bg-white/30"
        }"></span>`;
      })
      .join("");
  }

  function showActive() {
    if (notices.length === 0) {
      renderIdle();
      return;
    }
    renderNotice(notices[activeIndex]);
    renderDots();
  }

  function startRotation() {
    if (rotateTimer) clearInterval(rotateTimer);
    if (notices.length <= 1) return;
    rotateTimer = setInterval(() => {
      activeIndex = (activeIndex + 1) % notices.length;
      showActive();
    }, cfg.rotateSeconds * 1000);
  }

  // ---------- polling ----------

  function computeSignature(list) {
    return JSON.stringify(list.map((n) => `${n.id}:${n.updated_at}`));
  }

  function poll() {
    fetch(cfg.apiUrl, { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error("bad response");
        return res.json();
      })
      .then((data) => {
        const incoming = data.notices || [];
        const newSignature = computeSignature(incoming);
        if (newSignature === signature) return; // nothing changed, keep current view/rotation as-is

        signature = newSignature;
        notices = incoming;
        activeIndex = 0;
        showActive();
        startRotation();
      })
      .catch(() => {
        // Network hiccup: keep showing the last known content instead of blanking the board.
      });
  }

  poll();
  setInterval(poll, cfg.pollSeconds * 1000);
})();
