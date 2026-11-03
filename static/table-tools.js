/* Elipsis — table tools: client-side search, column sort, CSV export.
   Attaches automatically to any table with data-table-tools="true".
   No dependencies. Progressive enhancement: without JS the table renders as-is. */
(function () {
  "use strict";

  const CSV_MIME = "text/csv;charset=utf-8";

  function cellText(cell) {
    return (cell.textContent || "").replace(/\s+/g, " ").trim();
  }

  function cellValue(cell) {
    // Prefer an explicit numeric value, then fall back to text.
    const explicit = cell.getAttribute("data-value");
    if (explicit !== null && explicit !== "") {
      const num = Number(explicit);
      if (!Number.isNaN(num)) return num;
      return explicit.toLowerCase();
    }
    const text = cellText(cell);
    const num = Number(text.replace(/[^0-9.\-]/g, ""));
    if (text && !Number.isNaN(num) && /[0-9]/.test(text)) return num;
    return text.toLowerCase();
  }

  function csvEscape(value) {
    const s = String(value == null ? "" : value);
    if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function download(filename, content) {
    const blob = new Blob(["\uFEFF" + content], { type: CSV_MIME }); // BOM for Excel
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function buildCsv(table) {
    const head = Array.from(table.querySelectorAll("thead th"))
      .map((th) => csvEscape(cellText(th)))
      .filter((v, i, arr) => !(i === arr.length - 1 && v === "")); // drop empty trailing action col
    const rows = Array.from(table.querySelectorAll("tbody tr"))
      .filter((tr) => !tr.classList.contains("is-filtered-out"))
      .map((tr) => Array.from(tr.children)
        .slice(0, head.length)
        .map((td) => csvEscape(cellText(td))));
    return head.join(",") + "\r\n" + rows.map((r) => r.join(",")).join("\r\n");
  }

  function enhance(table) {
    if (table.dataset.toolsReady === "true") return;
    table.dataset.toolsReady = "true";

    const headers = Array.from(table.querySelectorAll("thead th"));
    const body = table.querySelector("tbody");
    if (!body) return;
    const rows = Array.from(body.querySelectorAll("tr"));

    /* Toolbar ---------------------------------------------------------------- */
    const tools = document.createElement("div");
    tools.className = "table-tools";

    const search = document.createElement("input");
    search.type = "search";
    search.setAttribute("aria-label", "Search this table");
    search.placeholder = "Filter rows…";

    const exportBtn = document.createElement("button");
    exportBtn.type = "button";
    exportBtn.className = "btn ghost sm";
    exportBtn.textContent = "Export CSV";

    const count = document.createElement("span");
    count.className = "table-count";

    tools.append(search, exportBtn, count);
    table.parentNode.insertBefore(tools, table);

    const emptyNote = document.createElement("p");
    emptyNote.className = "table-empty-note";
    emptyNote.textContent = "No rows match this filter.";
    table.parentNode.insertBefore(emptyNote, table.nextSibling);

    /* Filtering -------------------------------------------------------------- */
    function applyFilter() {
      const needle = search.value.trim().toLowerCase();
      let visible = 0;
      rows.forEach((row) => {
        const text = Array.from(row.children).map(cellText).join(" ").toLowerCase();
        const show = !needle || text.includes(needle);
        row.classList.toggle("is-filtered-out", !show);
        if (show) visible++;
      });
      count.textContent = visible === rows.length
        ? rows.length + " rows"
        : visible + " of " + rows.length + " rows";
      emptyNote.classList.toggle("is-visible", visible === 0 && rows.length > 0);
    }
    search.addEventListener("input", applyFilter);

    /* Sorting ---------------------------------------------------------------- */
    let sortIndex = -1;
    let sortDir = 1;

    headers.forEach((th, index) => {
      const label = cellText(th);
      if (!label) return; // skip the trailing action column
      th.setAttribute("data-sortable", "true");
      th.setAttribute("role", "columnheader");
      th.setAttribute("aria-sort", "none");
      th.tabIndex = 0;

      function sort() {
        if (sortIndex === index) sortDir = -sortDir;
        else { sortIndex = index; sortDir = 1; }
        headers.forEach((h, i) => {
          h.classList.remove("sort-asc", "sort-desc");
          h.setAttribute("aria-sort", "None");
        });
        th.classList.add(sortDir === 1 ? "sort-asc" : "sort-desc");
        th.setAttribute("aria-sort", sortDir === 1 ? "ascending" : "descending");

        const sorted = rows.slice().sort((a, b) => {
          const av = cellValue(a.children[index]);
          const bv = cellValue(b.children[index]);
          if (typeof av === "number" && typeof bv === "number") return (av - bv) * sortDir;
          return String(av).localeCompare(String(bv)) * sortDir;
        });
        const fragment = document.createDocumentFragment();
        sorted.forEach((row) => fragment.appendChild(row));
        body.appendChild(fragment);
      }

      th.addEventListener("click", sort);
      th.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          sort();
        }
      });
    });

    /* Export ----------------------------------------------------------------- */
    exportBtn.addEventListener("click", () => {
      const name = (document.title || "elipsis-export").replace(/[^\w\-]+/g, "-").toLowerCase();
      download(name + ".csv", buildCsv(table));
    });

    applyFilter();
  }

  document.querySelectorAll('table[data-table-tools="true"]').forEach(enhance);
})();
