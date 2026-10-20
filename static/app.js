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

  /* Keyboard: escape closes, "/" focuses workspace search ------------------- */
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && layout && layout.classList.contains("sidebar-open")) {
      setSidebar(false);
      if (openBtn) openBtn.focus();
    }
    if (event.key === "Escape" && pubNav && pubNav.classList.contains("open")) {
      pubNav.classList.remove("open");
      if (pubToggle) {
        pubToggle.setAttribute("aria-expanded", "false");
        pubToggle.focus();
      }
    }
    const tag = (event.target && event.target.tagName || "").toLowerCase();
    const typing = tag === "input" || tag === "textarea" || tag === "select" || event.target.isContentEditable;
    if (event.key === "/" && !typing && !event.metaKey && !event.ctrlKey && !event.altKey) {
      const search = $(".topbar-search input[type='search']");
      if (search) {
        event.preventDefault();
        search.focus();
        search.select();
      }
    }
  });

  /* Copy-to-clipboard ------------------------------------------------------- */
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
