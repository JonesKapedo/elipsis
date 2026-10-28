/* Elipsis theme bootstrap — load before paint when possible */
(function () {
  try {
    var match = document.cookie.match(/(?:^|; )elipsis_theme=([^;]*)/);
    var pref = match ? decodeURIComponent(match[1]) : "system";
    if (pref !== "light" && pref !== "dark" && pref !== "system") pref = "system";
    var resolved = pref === "system"
      ? (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : pref;
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.setAttribute("data-theme-pref", pref);
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "light");
  }
  if (!document.querySelector('link[href*="theme.css"]')) {
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/static/theme.css?v=20261028d";
    document.head.appendChild(link);
  }
})();
