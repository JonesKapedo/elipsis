/* Elipsis app entry: theme first, then full interface behaviour */
(function () {
  var s = document.createElement("script");
  s.src = "/static/theme-boot.js?v=20261028d";
  document.head.appendChild(s);
  var l = document.createElement("link");
  l.rel = "stylesheet";
  l.href = "/static/theme.css?v=20261028d";
  document.head.appendChild(l);
})();

(function () {
  var url = "https://raw.githubusercontent.com/JonesKapedo/elipsis/a778c5c0d840b76fe575de4aa36b7cfa26084817/static/app.js";
  fetch(url)
    .then(function (r) { return r.text(); })
    .then(function (code) {
      var s = document.createElement("script");
      s.textContent = code;
      document.head.appendChild(s);
    })
    .catch(function () {
      console.warn("[elipsis] could not load full app shell");
    });
})();
