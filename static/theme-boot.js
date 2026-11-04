/* Elipsis theme bootstrap — load before paint when possible */
(function () {
  try {
    var match = document.cookie.match(/(?:^|; )elipsis_theme=([^;]*)/);
    var isPublic = document.documentElement.getAttribute("data-public") === "true";
    var pref = match ? decodeURIComponent(match[1]) : (isPublic ? "light" : "dark");
    if (isPublic) pref = "light";
    else if (pref !== "light" && pref !== "dark" && pref !== "system") pref = "system";
    var resolved = pref === "system"
      ? (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : pref;
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.setAttribute("data-theme-pref", pref);
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();
