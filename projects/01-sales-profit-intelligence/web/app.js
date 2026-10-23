(() => {
  "use strict";

  const REQUIRED_COLUMNS = [
    "order_date", "product", "category", "region",
    "units_sold", "unit_price", "unit_cost", "discount_rate",
  ];
  const COLORS = { revenue: "#3779c8", profit: "#3d9876", category: "#168b83", region: "#6d8ed0" };
  const state = { rows: [], chartInstances: {}, minimumDate: "", maximumDate: "" };
  const byId = (id) => document.getElementById(id);
  const elements = {
    dashboard: byId("dashboard"),
    loadError: byId("loadError"),
    recordStatus: byId("recordStatus"),
    periodLabel: byId("periodLabel"),
    startDate: byId("startDate"),
    endDate: byId("endDate"),
    resetFilters: byId("resetFilters"),
    insightsGrid: byId("insightsGrid"),
    chartError: byId("chartError"),
  };

  const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const moneyFormat = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: true,
  });
  const percentFormat = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });

  // Keep monetary values as exact base-10 decimals, matching
  // src/sales_profit_metrics.py. Binary floats can move half-cent ties.
  const ZERO = { coefficient: 0n, scale: 0 };
  function decimalFromText(value) {
    const match = /^([+-]?)(\d+)(?:\.(\d*))?$/.exec(String(value).trim());
    if (!match) throw new Error(`Invalid decimal value: ${value}`);
    const fraction = match[3] || "";
    const sign = match[1] === "-" ? -1n : 1n;
    return { coefficient: sign * BigInt(`${match[2]}${fraction}`), scale: fraction.length };
  }
  function decimalAdd(left, right) {
    const scale = Math.max(left.scale, right.scale);
    return {
      coefficient: left.coefficient * (10n ** BigInt(scale - left.scale))
        + right.coefficient * (10n ** BigInt(scale - right.scale)),
      scale,
    };
  }
  function decimalSubtract(left, right) {
    return decimalAdd(left, { coefficient: -right.coefficient, scale: right.scale });
  }
  function decimalCompare(left, right) {
    const difference = decimalSubtract(left, right).coefficient;
    return difference < 0n ? -1 : difference > 0n ? 1 : 0;
  }
  function decimalMultiply(left, right) {
    return { coefficient: left.coefficient * right.coefficient, scale: left.scale + right.scale };
  }
  function decimalToNumber(value) {
    return Number(value.coefficient) / (10 ** value.scale);
  }
  function centsHalfUp(value) {
    if (value.scale <= 2) return value.coefficient * (10n ** BigInt(2 - value.scale));
    const divisor = 10n ** BigInt(value.scale - 2);
    const magnitude = value.coefficient < 0n ? -value.coefficient : value.coefficient;
    let cents = magnitude / divisor;
    if ((magnitude % divisor) * 2n >= divisor) cents += 1n;
    return value.coefficient < 0n ? -cents : cents;
  }
  function formatMoney(value) {
    const cents = centsHalfUp(value);
    const magnitude = cents < 0n ? -cents : cents;
    const whole = (magnitude / 100n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    const fraction = (magnitude % 100n).toString().padStart(2, "0");
    return `${cents < 0n ? "-" : ""}${whole}.${fraction}`;
  }
  function formatRatioPercent(numerator, denominator) {
    if (denominator.coefficient === 0n) return "N/A";
    let top = numerator.coefficient < 0n ? -numerator.coefficient : numerator.coefficient;
    let bottom = denominator.coefficient < 0n ? -denominator.coefficient : denominator.coefficient;
    top *= 10n ** BigInt(denominator.scale) * 1000n;
    bottom *= 10n ** BigInt(numerator.scale);
    let tenths = top / bottom;
    if ((top % bottom) * 2n >= bottom) tenths += 1n;
    const signedTenths = (numerator.coefficient < 0n) !== (denominator.coefficient < 0n) ? -tenths : tenths;
    const magnitude = signedTenths < 0n ? -signedTenths : signedTenths;
    return `${signedTenths < 0n ? "-" : ""}${magnitude / 10n}.${magnitude % 10n}%`;
  }

  function parseCsv(source) {
    const records = [];
    let row = [];
    let cell = "";
    let quoted = false;
    for (let index = 0; index < source.length; index += 1) {
      const character = source[index];
      if (quoted) {
        if (character === '"' && source[index + 1] === '"') {
          cell += '"';
          index += 1;
        } else if (character === '"') {
          quoted = false;
        } else {
          cell += character;
        }
      } else if (character === '"' && cell.length === 0) {
        quoted = true;
      } else if (character === ",") {
        row.push(cell);
        cell = "";
      } else if (character === "\n" || character === "\r") {
        if (character === "\r" && source[index + 1] === "\n") index += 1;
        row.push(cell);
        if (row.some((value) => value.trim() !== "")) records.push(row);
        row = [];
        cell = "";
      } else {
        cell += character;
      }
    }
    if (quoted) throw new Error("The sales CSV contains an unterminated quoted field.");
    row.push(cell);
    if (row.some((value) => value.trim() !== "")) records.push(row);
    if (records.length < 2) throw new Error("The sales CSV has no data rows.");

    const headers = records[0].map((header, index) => (index === 0 ? header.replace(/^\uFEFF/, "") : header).trim());
    const missing = REQUIRED_COLUMNS.filter((column) => !headers.includes(column));
    if (missing.length) throw new Error(`The sales CSV is missing required columns: ${missing.join(", ")}.`);

    const headerIndexes = Object.fromEntries(REQUIRED_COLUMNS.map((column) => [column, headers.indexOf(column)]));
    const rows = [];
    let skippedRows = 0;
    records.slice(1).forEach((fields, dataIndex) => {
      if (fields.length !== headers.length) {
        throw new Error(`CSV row ${dataIndex + 2} has ${fields.length} fields; expected ${headers.length}.`);
      }
      const raw = Object.fromEntries(REQUIRED_COLUMNS.map((column) => [column, fields[headerIndexes[column]].trim()]));
      const units = Number(raw.units_sold);
      const unitPriceNumber = Number(raw.unit_price);
      const unitCostNumber = Number(raw.unit_cost);
      const discountRateNumber = Number(raw.discount_rate);
      const validDate = /^\d{4}-\d{2}-\d{2}$/.test(raw.order_date)
        && !Number.isNaN(Date.parse(`${raw.order_date}T00:00:00Z`))
        && new Date(`${raw.order_date}T00:00:00Z`).toISOString().slice(0, 10) === raw.order_date;
      const validDimensions = Boolean(raw.product && raw.category && raw.region);
      const validNumbers = [units, unitPriceNumber, unitCostNumber, discountRateNumber].every(Number.isFinite)
        && Number.isInteger(units) && units >= 0
        && unitPriceNumber >= 0 && unitCostNumber >= 0
        && discountRateNumber >= 0 && discountRateNumber <= 1;
      if (!validDate || !validDimensions || !validNumbers) {
        skippedRows += 1;
        return;
      }

      // Match the canonical Decimal metric policy and operation order.
      const exactUnits = decimalFromText(raw.units_sold);
      const grossSales = decimalMultiply(exactUnits, decimalFromText(raw.unit_price));
      const discountAmount = decimalMultiply(grossSales, decimalFromText(raw.discount_rate));
      const revenue = decimalSubtract(grossSales, discountAmount);
      const cost = decimalMultiply(exactUnits, decimalFromText(raw.unit_cost));
      const profit = decimalSubtract(revenue, cost);
      rows.push({
        date: raw.order_date,
        month: raw.order_date.slice(0, 7),
        product: raw.product,
        category: raw.category,
        region: raw.region,
        units,
        grossSales,
        discountAmount,
        revenue,
        cost,
        profit,
      });
    });
    if (!rows.length) throw new Error("The sales CSV has no valid records after checking dates, dimensions, and numeric values.");
    return { rows, skippedRows };
  }

  async function loadSalesData() {
    const response = await fetch("../data/sales_data.csv", { cache: "no-store" });
    if (!response.ok) throw new Error(`Could not load data/sales_data.csv (HTTP ${response.status}).`);
    const source = await response.text();
    const parsed = parseCsv(source);
    state.rows = parsed.rows;
    state.minimumDate = state.rows.reduce((minimum, row) => row.date < minimum ? row.date : minimum, state.rows[0].date);
    state.maximumDate = state.rows.reduce((maximum, row) => row.date > maximum ? row.date : maximum, state.rows[0].date);
    elements.startDate.min = state.minimumDate;
    elements.startDate.max = state.maximumDate;
    elements.endDate.min = state.minimumDate;
    elements.endDate.max = state.maximumDate;
    elements.startDate.value = state.minimumDate;
    elements.endDate.value = state.maximumDate;
    elements.periodLabel.textContent = `${formatDateLabel(state.minimumDate)} – ${formatDateLabel(state.maximumDate)}`;
    populateDimensionFilter("category", "categoryOptions", "categoryFilter");
    populateDimensionFilter("region", "regionOptions", "regionFilter");
    populateDimensionFilter("product", "productOptions", "productFilter");
    elements.dashboard.hidden = false;
    elements.recordStatus.textContent = parsed.skippedRows
      ? `Showing ${numberFormat.format(state.rows.length)} valid records · skipped ${numberFormat.format(parsed.skippedRows)} incomplete or invalid rows.`
      : `${numberFormat.format(state.rows.length)} synthetic sales records loaded`;
    updateDashboard();
  }

  function formatDateLabel(isoDate) {
    const [year, month, day] = isoDate.split("-").map(Number);
    return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })
      .format(new Date(Date.UTC(year, month - 1, day)));
  }

  function populateDimensionFilter(column, optionsId, detailsId) {
    const container = byId(optionsId);
    const values = [...new Set(state.rows.map((row) => row[column]))].sort((a, b) => a.localeCompare(b));
    container.replaceChildren();
    values.forEach((value, index) => {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = true;
      checkbox.value = value;
      checkbox.dataset.dimension = column;
      checkbox.id = `${column}-option-${index}`;
      const text = document.createElement("span");
      text.textContent = value;
      label.htmlFor = checkbox.id;
      label.append(checkbox, text);
      container.append(label);
    });
    updateFilterSummary(detailsId, column);
  }

  function selectedValues(column) {
    return [...document.querySelectorAll(`input[data-dimension="${column}"]:checked`)].map((input) => input.value);
  }

  function updateFilterSummary(detailsId, column) {
    const filter = byId(detailsId);
    const total = document.querySelectorAll(`input[data-dimension="${column}"]`).length;
    const selected = selectedValues(column).length;
    const summary = filter.querySelector(".filter-value");
    const plural = column === "category" ? "categories" : `${column}s`;
    if (selected === total) summary.textContent = `All ${plural}`;
    else if (selected === 0) summary.textContent = `No ${plural}`;
    else summary.textContent = `${selected} selected`;
  }

  function getFilteredRows() {
    let start = elements.startDate.value;
    let end = elements.endDate.value;
    if (!start || !end) return [];
    if (start > end) [start, end] = [end, start];
    const categories = new Set(selectedValues("category"));
    const regions = new Set(selectedValues("region"));
    const products = new Set(selectedValues("product"));
    return state.rows.filter((row) => row.date >= start && row.date <= end
      && categories.has(row.category) && regions.has(row.region) && products.has(row.product));
  }

  function aggregate(rows) {
    const totals = rows.reduce((result, row) => {
      result.records += 1;
      result.units += row.units;
      result.grossSales = decimalAdd(result.grossSales, row.grossSales);
      result.discountAmount = decimalAdd(result.discountAmount, row.discountAmount);
      result.revenue = decimalAdd(result.revenue, row.revenue);
      result.cost = decimalAdd(result.cost, row.cost);
      result.profit = decimalAdd(result.profit, row.profit);
      return result;
    }, { records: 0, units: 0, grossSales: ZERO, discountAmount: ZERO, revenue: ZERO, cost: ZERO, profit: ZERO });
    totals.margin = totals.revenue.coefficient !== 0n ? formatRatioPercent(totals.profit, totals.revenue) : "N/A";
    return totals;
  }

  function groupRows(rows, field) {
    const grouped = new Map();
    rows.forEach((row) => {
      if (!grouped.has(row[field])) grouped.set(row[field], []);
      grouped.get(row[field]).push(row);
    });
    return [...grouped.entries()].map(([key, group]) => ({ key, ...aggregate(group) }));
  }

  function formatPercent(value) { return value; }
  function formatCompact(value) {
    return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
  }

  function updateKpis(rows) {
    const totals = aggregate(rows);
    byId("kpiRevenue").textContent = formatMoney(totals.revenue);
    byId("kpiProfit").textContent = formatMoney(totals.profit);
    byId("kpiMargin").textContent = rows.length ? formatPercent(totals.margin) : "N/A";
    byId("kpiUnits").textContent = numberFormat.format(totals.units);
    byId("kpiRecords").textContent = numberFormat.format(totals.records);
    elements.recordStatus.textContent = rows.length
      ? `${numberFormat.format(rows.length)} of ${numberFormat.format(state.rows.length)} records in selection`
      : "No records match the current filters.";
  }

  function insightCard(title, detail) {
    const card = document.createElement("article");
    card.className = "insight-card";
    const heading = document.createElement("h3");
    heading.textContent = title;
    const description = document.createElement("p");
    description.textContent = detail;
    card.append(heading, description);
    return card;
  }

  function updateInsights(rows) {
    elements.insightsGrid.replaceChildren();
    if (!rows.length) {
      elements.insightsGrid.append(insightCard("No matching records", "Adjust the filters or use Reset to restore the complete synthetic sample."));
      return;
    }
    const totals = aggregate(rows);
    const products = groupRows(rows, "product").sort((a, b) => decimalCompare(b.profit, a.profit));
    const categories = groupRows(rows, "category").sort((a, b) => decimalCompare(b.revenue, a.revenue));
    const regions = groupRows(rows, "region").sort((a, b) => decimalCompare(b.profit, a.profit));
    const months = groupRows(rows, "month").sort((a, b) => a.key.localeCompare(b.key));
    const topProduct = products[0];
    const topCategory = categories[0];
    const topRegion = regions[0];
    const categoryShare = formatPercent(formatRatioPercent(topCategory.revenue, totals.revenue));

    elements.insightsGrid.append(
      insightCard("Product profit leader", `${topProduct.key} contributes ${formatMoney(topProduct.profit)} calculated profit at a ${formatPercent(topProduct.margin)} aggregate margin.`),
      insightCard("Largest category by revenue", `${topCategory.key} records ${formatMoney(topCategory.revenue)} in revenue after discounts (${categoryShare} of this selection).`),
      insightCard("Regional profit leader", `${topRegion.key} records ${formatMoney(topRegion.profit)} calculated profit at a ${formatPercent(topRegion.margin)} aggregate margin.`),
    );
    if (months.length > 1) {
      const first = months[0];
      const last = months[months.length - 1];
      const detail = first.revenue.coefficient !== 0n
        ? `Revenue after discounts was ${formatMoney(first.revenue)} in ${monthLabel(first.key)} and ${formatMoney(last.revenue)} in ${monthLabel(last.key)} (${formatPercent(formatRatioPercent(decimalSubtract(last.revenue, first.revenue), first.revenue))} between endpoints). This does not describe every month between them.`
        : `Revenue after discounts was ${formatMoney(first.revenue)} in ${monthLabel(first.key)} and ${formatMoney(last.revenue)} in ${monthLabel(last.key)}. The first period has no revenue for a percentage comparison.`;
      elements.insightsGrid.append(insightCard("First-to-last active month", detail));
    } else if (months.length === 1) {
      elements.insightsGrid.append(insightCard("Selected month", `${monthLabel(months[0].key)} contains ${numberFormat.format(months[0].records)} matching records.`));
    }
  }

  function monthLabel(isoMonth) {
    const [year, month] = isoMonth.split("-").map(Number);
    return new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone: "UTC" })
      .format(new Date(Date.UTC(year, month - 1, 1)));
  }

  function commonOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 180 },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { color: "#6f8091", boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: "circle", padding: 13, font: { family: "DM Sans", size: 9 } } },
        tooltip: { backgroundColor: "#152b45", titleFont: { family: "DM Sans", size: 10 }, bodyFont: { family: "DM Sans", size: 10 }, padding: 9, callbacks: { label: (context) => `${context.dataset.label}: ${formatMoney(context.dataset.exactValues?.[context.dataIndex] ?? decimalFromText(String(context.parsed.y ?? context.parsed.x)))}` } },
      },
      scales: {
        x: { grid: { color: "#edf1f4", drawBorder: false }, border: { display: false }, ticks: { color: "#8392a2", maxRotation: 0, autoSkip: true, font: { family: "DM Sans", size: 8 }, callback: (value) => formatCompact(value) } },
        y: { grid: { color: "#edf1f4", drawBorder: false }, border: { display: false }, ticks: { color: "#65788d", font: { family: "DM Sans", size: 9 }, precision: 0 } },
      },
    };
  }

  function chartConfig(type, labels, datasets, options = {}) {
    const base = commonOptions();
    return { type, data: { labels, datasets }, options: { ...base, ...options, plugins: { ...base.plugins, ...(options.plugins || {}) }, scales: options.scales || base.scales } };
  }

  function upsertChart(id, config) {
    const canvas = byId(id);
    const chart = state.chartInstances[id];
    if (!chart) {
      state.chartInstances[id] = new Chart(canvas, config);
      return;
    }
    chart.data.labels = config.data.labels;
    chart.data.datasets = config.data.datasets;
    chart.options = config.options;
    chart.update();
  }

  function updateCharts(rows) {
    if (typeof Chart === "undefined") {
      elements.chartError.hidden = false;
      return;
    }
    elements.chartError.hidden = true;
    const empty = rows.length === 0;
    document.querySelectorAll(".chart-wrap").forEach((container) => {
      const canvas = container.querySelector("canvas");
      const message = container.querySelector(".chart-empty");
      canvas.hidden = empty;
      message.hidden = !empty;
    });

    const monthly = groupRows(rows, "month").sort((a, b) => a.key.localeCompare(b.key));
    const products = groupRows(rows, "product").sort((a, b) => decimalCompare(b.profit, a.profit));
    const categories = groupRows(rows, "category").sort((a, b) => decimalCompare(b.profit, a.profit));
    const regions = groupRows(rows, "region").sort((a, b) => decimalCompare(b.profit, a.profit));
    const gridColor = "#e8edf2";
    const trendOptions = {
      ...commonOptions(),
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ...commonOptions().scales.x, grid: { display: false }, ticks: { ...commonOptions().scales.x.ticks, callback: (value, index) => monthLabel(monthly[index]?.key || "") } },
        y: { ...commonOptions().scales.y, grid: { color: gridColor }, ticks: { ...commonOptions().scales.y.ticks, callback: (value) => formatCompact(value) } },
      },
      plugins: { ...commonOptions().plugins, tooltip: { ...commonOptions().plugins.tooltip, callbacks: { label: (context) => `${context.dataset.label}: ${formatMoney(context.dataset.exactValues[context.dataIndex])}` } } },
    };
    upsertChart("trendChart", chartConfig("line", monthly.map((item) => item.key), [
      { label: "Revenue after discounts", data: monthly.map((item) => decimalToNumber(item.revenue)), exactValues: monthly.map((item) => item.revenue), borderColor: COLORS.revenue, backgroundColor: "rgba(55,121,200,.08)", borderWidth: 2, pointRadius: 2.5, pointHoverRadius: 4, tension: .28, fill: true },
      { label: "Calculated profit", data: monthly.map((item) => decimalToNumber(item.profit)), exactValues: monthly.map((item) => item.profit), borderColor: COLORS.profit, backgroundColor: "transparent", borderWidth: 2, pointRadius: 2.5, pointHoverRadius: 4, tension: .28 },
    ], trendOptions));

    const productOptions = {
      ...commonOptions(),
      indexAxis: "y",
      interaction: { mode: "nearest", intersect: true },
      scales: {
        x: { ...commonOptions().scales.x, grid: { color: gridColor }, ticks: { ...commonOptions().scales.x.ticks, callback: (value) => formatCompact(value) } },
        y: { ...commonOptions().scales.y, grid: { display: false }, ticks: { ...commonOptions().scales.y.ticks, autoSkip: false } },
      },
      plugins: { ...commonOptions().plugins, legend: { display: false }, tooltip: { ...commonOptions().plugins.tooltip, callbacks: { label: (context) => `Calculated profit: ${formatMoney(context.dataset.exactValues[context.dataIndex])}` } } },
    };
    upsertChart("productChart", chartConfig("bar", products.map((item) => item.key), [
      { label: "Calculated profit", data: products.map((item) => decimalToNumber(item.profit)), exactValues: products.map((item) => item.profit), backgroundColor: products.map((_, index) => index === 0 ? "#3d9876" : "#83b6a0"), borderRadius: 3, maxBarThickness: 18 },
    ], productOptions));

    function groupedBarOptions(labels) {
      const base = commonOptions();
      return {
        ...base,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { ...base.scales.x, grid: { display: false }, ticks: { ...base.scales.x.ticks, autoSkip: false, callback: (_value, index) => labels[index] || "" } },
          y: { ...base.scales.y, grid: { color: gridColor }, ticks: { ...base.scales.y.ticks, callback: (value) => formatCompact(value) } },
        },
        plugins: { ...base.plugins, tooltip: { ...base.plugins.tooltip, callbacks: { label: (context) => `${context.dataset.label}: ${formatMoney(context.dataset.exactValues[context.dataIndex])}` } } },
      };
    }
    upsertChart("categoryChart", chartConfig("bar", categories.map((item) => item.key), [
      { label: "Revenue after discounts", data: categories.map((item) => decimalToNumber(item.revenue)), exactValues: categories.map((item) => item.revenue), backgroundColor: COLORS.revenue, borderRadius: 3, maxBarThickness: 23 },
      { label: "Calculated profit", data: categories.map((item) => decimalToNumber(item.profit)), exactValues: categories.map((item) => item.profit), backgroundColor: COLORS.profit, borderRadius: 3, maxBarThickness: 23 },
    ], groupedBarOptions(categories.map((item) => item.key))));
    upsertChart("regionChart", chartConfig("bar", regions.map((item) => item.key), [
      { label: "Revenue after discounts", data: regions.map((item) => decimalToNumber(item.revenue)), exactValues: regions.map((item) => item.revenue), backgroundColor: COLORS.revenue, borderRadius: 3, maxBarThickness: 23 },
      { label: "Calculated profit", data: regions.map((item) => decimalToNumber(item.profit)), exactValues: regions.map((item) => item.profit), backgroundColor: COLORS.region, borderRadius: 3, maxBarThickness: 23 },
    ], groupedBarOptions(regions.map((item) => item.key))));
  }

  function updateDashboard() {
    let periodStart = elements.startDate.value || state.minimumDate;
    let periodEnd = elements.endDate.value || state.maximumDate;
    if (periodStart > periodEnd) [periodStart, periodEnd] = [periodEnd, periodStart];
    elements.periodLabel.textContent = `${formatDateLabel(periodStart)} – ${formatDateLabel(periodEnd)}`;
    const rows = getFilteredRows();
    updateKpis(rows);
    updateCharts(rows);
    updateInsights(rows);
  }

  function resetFilters() {
    elements.startDate.value = state.minimumDate;
    elements.endDate.value = state.maximumDate;
    document.querySelectorAll("input[data-dimension]").forEach((checkbox) => { checkbox.checked = true; });
    ["categoryFilter", "regionFilter", "productFilter"].forEach((id) => byId(id).open = false);
    ["category", "region", "product"].forEach((dimension) => updateFilterSummary(`${dimension}Filter`, dimension));
    updateDashboard();
  }

  [elements.startDate, elements.endDate].forEach((input) => input.addEventListener("change", updateDashboard));
  document.querySelectorAll(".filter-menu").forEach((menu) => {
    menu.addEventListener("toggle", () => {
      if (!menu.open) return;
      document.querySelectorAll(".filter-menu").forEach((otherMenu) => {
        if (otherMenu !== menu) otherMenu.open = false;
      });
    });
    menu.addEventListener("change", (event) => {
      const dimension = event.target.dataset.dimension;
      if (dimension) updateFilterSummary(`${dimension}Filter`, dimension);
      updateDashboard();
    });
  });
  elements.resetFilters.addEventListener("click", resetFilters);

  loadSalesData().catch((error) => {
    elements.loadError.textContent = `The dashboard could not load the sales data. ${error.message} Start a local web server from the project folder or check the GitHub Pages data path, then reload.`;
    elements.loadError.hidden = false;
    elements.recordStatus.textContent = "Data unavailable";
    elements.periodLabel.textContent = "Data unavailable";
  });
})();
