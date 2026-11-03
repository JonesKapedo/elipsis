/* Elipsis theme bootstrap — applied by this entry script before shell behaviour.
   base.html loads theme.css statically; this resolves the saved theme preference
   from the cookie as early as the entry script runs (preserves prior behaviour). */
(function () {
  var s = document.createElement("script");
  s.src = "/static/theme-boot.js?v=20261102a";
  document.head.appendChild(s);
})();

/* Elipsis — shared interface behaviour. No dependencies. */
(function () {
  "use strict";

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  /* App shell: mobile sidebar ------------------------------------------------ */
  const layout = $(".app-layout");
  const sidebar = $("#app-sidebar");
  const openBtn = $("#sidebar-toggle");
  const closeBtn = $("#sidebar-close");
  const backdrop = $("#sidebar-backdrop");

  function setSidebar(open) {
    if (!layout) return;
    layout.classList.toggle("sidebar-open", open);
    document.body.classList.toggle("nav-open", open);
    if (openBtn) openBtn.setAttribute("aria-expanded", open ? "true" : "false");
    if (backdrop) backdrop.setAttribute("aria-hidden", open ? "false" : "true");
    if (open && sidebar) {
      const first = sidebar.querySelector("a, button");
      if (first) first.focus({ preventScroll: true });
    }
  }

  if (openBtn) openBtn.addEventListener("click", () => setSidebar(true));
  if (closeBtn) closeBtn.addEventListener("click", () => setSidebar(false));
  if (backdrop) backdrop.addEventListener("click", () => setSidebar(false));
  if (sidebar) {
    sidebar.addEventListener("click", (event) => {
      if (window.matchMedia("(max-width: 900px)").matches && event.target.closest("a")) {
        setSidebar(false);
      }
    });
  }

  /* Public mobile menu ------------------------------------------------------ */
  const pubToggle = $("#pub-menu-toggle");
  const pubNav = $("#pub-nav");
  if (pubToggle && pubNav) {
    pubToggle.addEventListener("click", () => {
      const open = pubNav.classList.toggle("open");
      pubToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("click", (event) => {
      if (!pubNav.classList.contains("open")) return;
      if (event.target.closest("#pub-nav") || event.target.closest("#pub-menu-toggle")) return;
      pubNav.classList.remove("open");
      pubToggle.setAttribute("aria-expanded", "false");
    });
  }

  /* Theme quick-toggle ------------------------------------------------------ */
  const THEME_COOKIE = "elipsis_theme";
  const themeToggle = $("#theme-toggle");

  function currentThemePref() {
    const match = document.cookie.match(new RegExp("(?:^|; )" + THEME_COOKIE + "=([^;]*)"));
    const pref = match ? decodeURIComponent(match[1]) : "system";
    return (pref === "light" || pref === "dark" || pref === "system") ? pref : "system";
  }

  function resolvedTheme() {
    const pref = currentThemePref();
    if (pref === "system") {
      return (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches)
        ? "dark" : "light";
    }
    return pref;
  }

  function applyTheme(pref) {
    const resolved = pref === "system"
      ? (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : pref;
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.setAttribute("data-theme-pref", pref);
  }

  function saveThemePref(pref) {
    // Mirror the server cookie (1 year) so theme-boot.js resolves it next load.
    const secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = THEME_COOKIE + "=" + encodeURIComponent(pref)
      + "; path=/; max-age=31536000; samesite=lax" + secure;
  }

  function toggleTheme() {
    const next = resolvedTheme() === "dark" ? "light" : "dark";
    saveThemePref(next);
    applyTheme(next);
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", toggleTheme);
  }

  /* Keyboard shortcuts help -------------------------------------------------- */
  const kbdHelp = $("#kbd-help");
  const kbdTrigger = $("#kbd-help-trigger");
  const kbdClose = $("#kbd-help-close");

  function kbdOpen() {
    if (!kbdHelp) return;
    if (typeof kbdHelp.showModal === "function" && !kbdHelp.open) kbdHelp.showModal();
    else if (!kbdHelp.open) kbdHelp.setAttribute("open", "");
    if (kbdClose) window.setTimeout(() => kbdClose.focus(), 20);
  }

  function kbdCloseDialog() {
    if (!kbdHelp) return;
    if (typeof kbdHelp.close === "function" && kbdHelp.open) kbdHelp.close();
    else kbdHelp.removeAttribute("open");
  }

  if (kbdTrigger) kbdTrigger.addEventListener("click", kbdOpen);
  if (kbdClose) kbdClose.addEventListener("click", kbdCloseDialog);
  if (kbdHelp) {
    kbdHelp.addEventListener("click", (event) => {
      if (event.target === kbdHelp) kbdCloseDialog();
    });
  }

  /* Command palette --------------------------------------------------------- */
  const cmdk = $("#cmdk");
  const cmdkInput = $("#cmdk-input");
  const cmdkResults = $("#cmdk-results");
  const cmdkTrigger = $("#cmd-trigger");
  let cmdkItems = [];
  let cmdkActive = 0;

  const commands = [
    { title: "New assessment", meta: "Start a diagnostic", href: "/start", icon: "+", keys: "create start diagnose" },
    { title: "Guided demo", meta: "Generate a complete logistics example", href: "/demo", icon: ">", keys: "demo example sample" },
    { title: "Action plan", meta: "Owners, dates, overdue work", href: "/actions", icon: "v", keys: "tasks board execution" },
    { title: "Assessments", meta: "Reports, drafts and comparisons", href: "/assessments", icon: "=", keys: "reports results compare" },
    { title: "Organisation", meta: "Company profile and team", href: "/company", icon: "#", keys: "company team people" },
    { title: "Marketplace", meta: "Private pilot status", href: "/marketplace", icon: "*", keys: "providers partners services" },
    { title: "Notifications", meta: "Unread work and review dates", href: "/notifications", icon: "o", keys: "inbox alerts digest" },
    { title: "Settings", meta: "Profile, webhooks and display", href: "/settings", icon: "%", keys: "preferences configuration" },
    { title: "Audit trail", meta: "Evidence, shares and changes", href: "/audit", icon: "~", keys: "history trust compliance" },
    { title: "Partner console", meta: "Client portfolio and white-label packs", href: "/partner", icon: "^", keys: "partner clients white label" },
    { title: "Workspace search", meta: "Search everything", href: "/search", icon: "?", keys: "find look up" },
    { title: "Sign out", meta: "End this session", href: "/logout", icon: "-", keys: "logout exit" }
  ];
  if (cmdk && cmdk.dataset.admin === "true") {
    commands.splice(commands.length - 1, 0,
      { title: "Admin pulse", meta: "Platform operations", href: "/admin", icon: "@", keys: "admin overview" },
      { title: "Request desk", meta: "Physical assessment requests", href: "/admin/requests", icon: "$", keys: "admin requests" }
    );
  }

  function cmdkRender(query) {
    if (!cmdkResults) return;
    const raw = (query || "").trim();
    const needle = raw.toLowerCase();
    let list = commands.filter((item) =>
      !needle || (item.title + " " + item.meta + " " + item.keys).toLowerCase().includes(needle)
    );
    if (raw.length > 1) {
      list = list.concat([{
        title: "Search workspace for '" + raw + "'",
        meta: "Find organisations, assessments and actions",
        href: "/search?q=" + encodeURIComponent(raw),
        icon: "?",
        dynamic: true
      }]);
    }
    cmdkItems = list;
    cmdkActive = 0;
    cmdkResults.replaceChildren();
    if (!list.length) {
      const empty = document.createElement("p");
      empty.className = "cmdk-empty";
      empty.textContent = "No commands match. Try another phrase.";
      cmdkResults.appendChild(empty);
      return;
    }
    list.forEach((item, index) => {
      const link = document.createElement("a");
      link.className = "cmdk-item" + (index === 0 ? " active" : "");
      link.href = item.href;
      link.setAttribute("role", "option");
      link.setAttribute("aria-selected", index === 0 ? "true" : "false");
      link.dataset.index = String(index);
      const icon = document.createElement("span");
      icon.className = "cmdk-item-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = item.icon || "-";
      const body = document.createElement("span");
      body.className = "cmdk-item-body";
      const title = document.createElement("strong");
      title.textContent = item.title;
      const meta = document.createElement("span");
      meta.textContent = item.meta;
      body.append(title, meta);
      const enter = document.createElement("span");
      enter.className = "cmdk-enter";
      enter.setAttribute("aria-hidden", "true");
      enter.textContent = "Enter";
      link.append(icon, body, enter);
      link.addEventListener("pointerenter", () => cmdkSetActive(index));
      cmdkResults.appendChild(link);
    });
  }

  function cmdkSetActive(index) {
    if (!cmdkItems.length) return;
    cmdkActive = (index + cmdkItems.length) % cmdkItems.length;
    $$(".cmdk-item", cmdkResults).forEach((node, i) => {
      node.classList.toggle("active", i === cmdkActive);
      node.setAttribute("aria-selected", i === cmdkActive ? "true" : "false");
    });
  }

  function cmdkOpen() {
    if (!cmdk || !cmdkInput) return;
    if (typeof cmdk.showModal === "function" && !cmdk.open) cmdk.showModal();
    else if (!cmdk.open) cmdk.setAttribute("open", "");
    cmdkInput.value = "";
    cmdkRender("");
    window.setTimeout(() => cmdkInput.focus(), 20);
  }

  function cmdkClose() {
    if (!cmdk) return;
    if (typeof cmdk.close === "function" && cmdk.open) cmdk.close();
    else cmdk.removeAttribute("open");
  }

  if (cmdkTrigger) cmdkTrigger.addEventListener("click", cmdkOpen);
  if (cmdk) {
    cmdk.addEventListener("click", (event) => {
      if (event.target === cmdk) cmdkClose();
    });
    cmdk.addEventListener("close", () => {
      if (cmdkTrigger) cmdkTrigger.focus();
    });
  }
  if (cmdkInput) {
    cmdkInput.addEventListener("input", () => cmdkRender(cmdkInput.value));
    cmdkInput.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        cmdkSetActive(cmdkActive + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        cmdkSetActive(cmdkActive - 1);
      } else if (event.key === "Enter") {
        event.preventDefault();
        const item = cmdkItems[cmdkActive];
        if (item) window.location.assign(item.href);
      }
    });
  }

  /* Check-all for bulk action selection ------------------------------------- */
  $$("[data-check-all]").forEach((box) => {
    box.addEventListener("change", () => {
      const form = document.getElementById(box.dataset.checkAll);
      if (!form) return;
      $$('input[name="item_ids"]', form).forEach((input) => { input.checked = box.checked; });
    });
  });

  /* Keyboard: shortcuts work everywhere outside text fields ----------------- */
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (cmdk && cmdk.open) cmdkClose();
      else cmdkOpen();
      return;
    }
    if (event.key === "Escape") {
      if (layout && layout.classList.contains("sidebar-open")) {
        setSidebar(false);
        if (openBtn) openBtn.focus();
      }
      if (pubNav && pubNav.classList.contains("open")) {
        pubNav.classList.remove("open");
        if (pubToggle) {
          pubToggle.setAttribute("aria-expanded", "false");
          pubToggle.focus();
        }
      }
      if (kbdHelp && kbdHelp.open) kbdCloseDialog();
      return;
    }
    const tag = (event.target && event.target.tagName || "").toLowerCase();
    const typing = tag === "input" || tag === "textarea" || tag === "select" || event.target.isContentEditable;
    if (typing || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === "/") {
      const search = $(".topbar-search input[type='search']");
      if (search) {
        event.preventDefault();
        search.focus();
        search.select();
      }
    } else if (event.key === "?" || (event.shiftKey && event.key === "/")) {
      if (kbdHelp) {
        event.preventDefault();
        kbdOpen();
      }
    } else if (event.key.toLowerCase() === "t" && themeToggle) {
      event.preventDefault();
      toggleTheme();
    }
  });

  /* Copy-to-clipboard (data-copy holds the literal value) ------------------- */
  $$("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const value = button.getAttribute("data-copy") || "";
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        const original = button.textContent;
        button.textContent = "Copied";
        button.classList.add("copied");
        window.setTimeout(() => {
          button.textContent = original;
          button.classList.remove("copied");
        }, 1600);
      } catch (error) {
        const input = Array.from(document.querySelectorAll("input"))
          .find((node) => node.value === value);
        if (input) {
          input.focus();
          input.select();
        }
      }
    });
  });

  /* Accessible tabs --------------------------------------------------------- */
  $$(".tabs").forEach((tabs) => {
    tabs.classList.add("tabs-ready");
    const buttons = $$(".tab", tabs);
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        buttons.forEach((item) => {
          item.setAttribute("aria-selected", item === button ? "true" : "false");
          item.setAttribute("tabindex", item === button ? "0" : "-1");
        });
        $$(".tab-panel").forEach((panel) => {
          panel.classList.toggle("active", panel.id === button.getAttribute("aria-controls"));
        });
      });
    });
  });

  /* Confirm destructive forms ---------------------------------------------- */
  $$("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.getAttribute("data-confirm"))) event.preventDefault();
    });
  });

  /* Copy target text (data-copy-target is a selector) ---------------------- */
  $$("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.querySelector(button.getAttribute("data-copy-target"));
      if (!target) return;
      try {
        await navigator.clipboard.writeText(target.value || target.textContent || "");
        const previous = button.textContent;
        button.textContent = "Copied";
        button.classList.add("copied");
        window.setTimeout(() => { button.textContent = previous; button.classList.remove("copied"); }, 1800);
      } catch (err) {
        if (target.select) target.select();
        document.execCommand("copy");
      }
    });
  });

  /* Auto-dismiss flash messages -------------------------------------------- */
  $$(".flash.ok").forEach((flash) => {
    window.setTimeout(() => {
      flash.style.transition = "opacity .35s ease, transform .35s ease";
      flash.style.opacity = "0";
      flash.style.transform = "translateY(-4px)";
      window.setTimeout(() => flash.remove(), 400);
    }, 6000);
  });

  /* Respect reduced motion -------------------------------------------------- */
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduce && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    $$(".reveal").forEach((node) => observer.observe(node));
  } else {
    $$(".reveal").forEach((node) => node.classList.add("is-visible"));
  }
})();
