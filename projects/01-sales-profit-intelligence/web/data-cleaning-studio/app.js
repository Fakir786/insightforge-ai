(() => {
  "use strict";

  const MAX_FILE_BYTES = 20 * 1024 * 1024;
  const PAGE_SIZE = 25;
  const $ = (id) => document.getElementById(id);
  const state = { headers: [], originalHeaders: [], original: [], rows: [], fileName: "", page: 1, sheetName: "" };
  const ui = {
    dropZone: $("dropZone"), fileInput: $("fileInput"), workspace: $("workspace"),
    errorBox: $("errorBox"), fileName: $("fileName"), fileMeta: $("fileMeta"),
    rowCount: $("rowCount"), columnCount: $("columnCount"),
    duplicateCount: $("duplicateCount"), emptyCount: $("emptyCount"),
    tableHead: $("tableHead"), tableBody: $("tableBody"), previewMeta: $("previewMeta"),
    tableSearch: $("tableSearch"), pageInfo: $("pageInfo"),
    previousPage: $("previousPage"), nextPage: $("nextPage"), actionStatus: $("actionStatus")
  };

  function showError(message) {
    ui.errorBox.textContent = message;
    ui.errorBox.hidden = false;
  }
  function clearError() { ui.errorBox.hidden = true; ui.errorBox.textContent = ""; }
  function cellText(value) { return value == null ? "" : String(value); }
  function isBlank(value) { return cellText(value).trim() === ""; }
  function rowIsEmpty(row) { return row.every(isBlank); }
  function duplicateKey(row) { return JSON.stringify(row.map(cellText)); }

  function inspect(rows, headers) {
    const seen = new Set();
    let duplicates = 0;
    let emptyCells = 0;
    rows.forEach((row) => {
      if (seen.has(duplicateKey(row))) duplicates += 1;
      else seen.add(duplicateKey(row));
      row.forEach((value) => { if (isBlank(value)) emptyCells += 1; });
    });
    return { duplicates, emptyCells };
  }

  function updateMetrics() {
    const quality = inspect(state.rows, state.headers);
    ui.rowCount.textContent = state.rows.length.toLocaleString();
    ui.columnCount.textContent = state.headers.length.toLocaleString();
    ui.duplicateCount.textContent = quality.duplicates.toLocaleString();
    ui.emptyCount.textContent = quality.emptyCells.toLocaleString();
    ui.previewMeta.textContent = `${state.rows.length.toLocaleString()} rows · ${state.headers.length.toLocaleString()} columns · showing up to ${PAGE_SIZE} rows per page`;
  }

  function renderTable() {
    const query = ui.tableSearch.value.trim().toLocaleLowerCase();
    const filtered = state.rows.filter((row) => !query || row.some((value) => cellText(value).toLocaleLowerCase().includes(query)));
    const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    state.page = Math.min(state.page, pageCount);
    const start = (state.page - 1) * PAGE_SIZE;
    const visible = filtered.slice(start, start + PAGE_SIZE);

    const headerRow = document.createElement("tr");
    state.headers.forEach((header) => {
      const th = document.createElement("th");
      th.textContent = header;
      headerRow.append(th);
    });
    ui.tableHead.replaceChildren(headerRow);
    ui.tableBody.replaceChildren();
    if (!visible.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = Math.max(1, state.headers.length);
      td.textContent = "No matching rows.";
      tr.append(td);
      ui.tableBody.append(tr);
    } else {
      visible.forEach((row) => {
        const tr = document.createElement("tr");
        state.headers.forEach((_, index) => {
          const td = document.createElement("td");
          td.textContent = cellText(row[index]);
          td.title = cellText(row[index]);
          tr.append(td);
        });
        ui.tableBody.append(tr);
      });
    }
    ui.pageInfo.textContent = `Page ${state.page} of ${pageCount} · ${filtered.length.toLocaleString()} matching rows`;
    ui.previousPage.disabled = state.page <= 1;
    ui.nextPage.disabled = state.page >= pageCount;
  }

  function refresh() { updateMetrics(); renderTable(); }

  function parseCsvFile(file) {
    return new Promise((resolve, reject) => {
      Papa.parse(file, {
        skipEmptyLines: false,
        dynamicTyping: false,
        complete: (result) => {
          if (result.errors?.length) {
            const fatal = result.errors.find((error) => error.code !== "TooManyFields");
            if (fatal) return reject(new Error(`Could not read CSV: ${fatal.message}`));
          }
          const matrix = result.data.filter((row) => Array.isArray(row) && row.some((value) => !isBlank(value)));
          if (matrix.length < 2) return reject(new Error("The CSV must contain a header row and at least one data row."));
          const headers = matrix[0].map((value, index) => {
            const text = cellText(value).replace(/^\uFEFF/, "").trim();
            return text || `Column ${index + 1}`;
          });
          const rows = matrix.slice(1).map((row) => headers.map((_, index) => row[index] ?? ""));
          resolve({ headers, rows, sheetName: "" });
        },
        error: (error) => reject(error)
      });
    });
  }

  async function parseExcelFile(file) {
    if (typeof XLSX === "undefined") throw new Error("The Excel reader could not load. Check your internet connection and try again, or use CSV.");
    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: "array", cellDates: false });
    const sheetName = workbook.SheetNames[0];
    if (!sheetName) throw new Error("This Excel file does not contain a worksheet.");
    const matrix = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { header: 1, defval: "", raw: false, blankrows: false });
    if (matrix.length < 2) throw new Error("The first worksheet must contain a header row and at least one data row.");
    const width = Math.max(...matrix.map((row) => row.length));
    const headers = Array.from({ length: width }, (_, index) => {
      const text = cellText(matrix[0][index]).trim();
      return text || `Column ${index + 1}`;
    });
    const rows = matrix.slice(1).map((row) => headers.map((_, index) => row[index] ?? ""));
    return { headers, rows, sheetName };
  }

  async function loadFile(file) {
    clearError();
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) return showError("This file is larger than 20 MB. Please choose a smaller file.");
    const extension = file.name.split(".").pop().toLowerCase();
    if (!["csv", "xlsx", "xls"].includes(extension)) return showError("Unsupported file type. Please choose a CSV, XLSX, or XLS file.");
    try {
      const parsed = extension === "csv" ? await parseCsvFile(file) : await parseExcelFile(file);
      if (!parsed.headers.length) throw new Error("No columns were found in this file.");
      state.headers = parsed.headers.slice();
      state.originalHeaders = parsed.headers.slice();
      state.original = parsed.rows.map((row) => row.slice());
      state.rows = parsed.rows.map((row) => row.slice());
      state.fileName = file.name;
      state.sheetName = parsed.sheetName;
      state.page = 1;
      ui.fileName.textContent = file.name;
      ui.fileMeta.textContent = `${parsed.rows.length.toLocaleString()} data rows · ${parsed.headers.length.toLocaleString()} columns${parsed.sheetName ? ` · Worksheet: ${parsed.sheetName}` : ""}`;
      ui.tableSearch.value = "";
      ui.workspace.hidden = false;
      ui.dropZone.hidden = true;
      ui.actionStatus.textContent = "File loaded successfully.";
      refresh();
      ui.workspace.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      showError(error.message || "The file could not be processed.");
    }
  }

  function applyCleaning() {
    let rows = state.rows.map((row) => row.slice());
    let headers = state.headers.slice();
    const before = rows.length;
    if ($("trimWhitespace").checked) rows = rows.map((row) => row.map((value) => typeof value === "string" ? value.trim() : value));
    if ($("removeEmptyRows").checked) rows = rows.filter((row) => !rowIsEmpty(row));
    if ($("removeDuplicates").checked) {
      const seen = new Set();
      rows = rows.filter((row) => {
        const key = duplicateKey(row);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    }
    if ($("removeEmptyColumns").checked && headers.length) {
      const keep = headers.map((_, index) => rows.some((row) => !isBlank(row[index])));
      headers = headers.filter((_, index) => keep[index]);
      rows = rows.map((row) => row.filter((_, index) => keep[index]));
    }
    state.headers = headers;
    state.rows = rows;
    state.page = 1;
    const removed = before - rows.length;
    ui.actionStatus.textContent = `Cleaning applied. ${removed} empty or duplicate rows removed; ${headers.length} columns retained.`;
    refresh();
  }

  function resetData() {
    state.rows = state.original.map((row) => row.slice());
    state.headers = state.originalHeaders.slice();
    state.page = 1;
    ui.tableSearch.value = "";
    ui.actionStatus.textContent = "Restored the original imported data.";
    refresh();
  }

  function safeSpreadsheetValue(value) {
    const text = cellText(value);
    return /^[\s]*[=+@]|^[\s]*-[^0-9.]/.test(text) ? `'${text}` : text;
  }

  function downloadBlob(blob, name) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function baseName() { return state.fileName.replace(/\.[^.]+$/, "").replace(/[^a-z0-9-_]+/gi, "_") || "cleaned_data"; }

  function exportCsv() {
    const matrix = [state.headers, ...state.rows].map((row) => row.map(safeSpreadsheetValue));
    const csv = "\uFEFF" + Papa.unparse(matrix, { quotes: true, newline: "\r\n" });
    downloadBlob(new Blob([csv], { type: "text/csv;charset=utf-8;" }), `${baseName()}_cleaned.csv`);
  }

  function exportExcel() {
    if (typeof XLSX === "undefined") return showError("The Excel export library could not load. Check your internet connection or download CSV instead.");
    const safeRows = state.rows.map((row) => row.map((value) => safeSpreadsheetValue(value)));
    const sheet = XLSX.utils.aoa_to_sheet([state.headers, ...safeRows]);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, sheet, "Cleaned Data");
    XLSX.writeFile(workbook, `${baseName()}_cleaned.xlsx`);
  }

  ui.fileInput.addEventListener("change", (event) => loadFile(event.target.files[0]));
  ui.dropZone.addEventListener("dragover", (event) => { event.preventDefault(); ui.dropZone.classList.add("dragover"); });
  ui.dropZone.addEventListener("dragleave", () => ui.dropZone.classList.remove("dragover"));
  ui.dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    ui.dropZone.classList.remove("dragover");
    loadFile(event.dataTransfer.files[0]);
  });
  $("newFile").addEventListener("click", () => { ui.fileInput.value = ""; ui.workspace.hidden = true; ui.dropZone.hidden = false; clearError(); window.scrollTo({ top: 0, behavior: "smooth" }); });
  $("applyCleaning").addEventListener("click", applyCleaning);
  $("resetData").addEventListener("click", resetData);
  $("downloadCsv").addEventListener("click", exportCsv);
  $("downloadExcel").addEventListener("click", exportExcel);
  ui.tableSearch.addEventListener("input", () => { state.page = 1; renderTable(); });
  ui.previousPage.addEventListener("click", () => { state.page -= 1; renderTable(); });
  ui.nextPage.addEventListener("click", () => { state.page += 1; renderTable(); });
})();