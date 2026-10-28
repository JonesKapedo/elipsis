/* Load theme early */
(function(){
  var s=document.createElement('script');
  s.src='/static/theme-boot.js?v=20261028d';
  document.head.appendChild(s);
  var l=document.createElement('link');
  l.rel='stylesheet';
  l.href='/static/theme.css?v=20261028d';
  document.head.appendChild(l);
})();

/* Elipsis — shared interface behaviour. No dependencies. */
(function () {
  "use strict";

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

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

  const pubToggle = $("#pub-menu-toggle");
  const pubNav = $("#pub-nav");
  if (pubToggle && pubNav) {
    pubToggle.addEventListener("click", () => {
      const open = pubNav.classList.toggle("open");
      pubToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setSidebar(false);
      if (pubNav) pubNav.classList.remove("open");
    }
  });

  $$("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.getAttribute("data-confirm"))) event.preventDefault();
    });
  });

  $$("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.querySelector(button.getAttribute("data-copy"));
      if (!target) return;
      try {
        await navigator.clipboard.writeText(target.value || target.textContent || "");
        const previous = button.textContent;
        button.textContent = "Copied";
        window.setTimeout(() => { button.textContent = previous; }, 1800);
      } catch (err) {
        if (target.select) target.select();
      }
    });
  });

  $$(".flash.ok").forEach((flash) => {
    window.setTimeout(() => {
      flash.style.opacity = "0";
      window.setTimeout(() => flash.remove(), 400);
    }, 6000);
  });
})();
