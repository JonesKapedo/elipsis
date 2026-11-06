/* Elipsis theme bootstrap — load before paint when possible */
(function () {
  try {
    var match = document.cookie.match(/(?:^|; )elipsis_theme=([^;]*)/);
    var pref = match ? decodeURIComponent(match[1]) : "dark";
    if (pref !== "light" && pref !== "dark" && pref !== "system") pref = "dark";
    var resolved = pref === "system"
      ? (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : pref;
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.setAttribute("data-theme-pref", pref);
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();
