/**
 * QUANTUM TRADE TERMINAL - CORE FRONTEND ENGINE
 * High-performance state management, canvas charting, live ticker simulation,
 * and order execution workflows.
 */

// Application State
const state = {
  stocks: [],
  portfolio: null,
  marketSummary: {},
  selectedStockSymbol: "AAPL",
  activeChartTab: "performance", // 'performance' | 'stock'
  selectedSector: "ALL",
  searchQuery: "",
  autoTickEnabled: true,
  autoTickIntervalId: null,
  tickSpeed: 2500,
  
  // Trade Modal State
  activeTradeType: "BUY",
  tradeStock: null,
};

// ==========================================================================
// INITIALIZATION
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadInitialData();
  startAutoTick();
  window.addEventListener("resize", handleResize);
});

async function loadInitialData() {
  await Promise.all([fetchMarketData(), fetchPortfolioData()]);
  renderAll();
}

function handleResize() {
  if (state.activeChartTab === "performance") {
    renderPortfolioPerformanceChart();
  } else {
    renderStockPriceChart();
  }
}

// ==========================================================================
// API DATA FETCHING
// ==========================================================================
async function fetchMarketData() {
  try {
    const res = await fetch("/api/market");
    if (!res.ok) throw new Error("Failed to load market data");
    const data = await res.json();
    state.stocks = data.stocks || [];
    state.marketSummary = data.summary || {};
  } catch (err) {
    showToast("Error loading market data: " + err.message, "error");
  }
}

async function fetchPortfolioData() {
  try {
    const res = await fetch("/api/portfolio");
    if (!res.ok) throw new Error("Failed to load portfolio data");
    state.portfolio = await res.json();
  } catch (err) {
    showToast("Error loading portfolio: " + err.message, "error");
  }
}

async function triggerTick(steps = 1) {
  try {
    const res = await fetch("/api/market/tick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ steps }),
    });
    if (!res.ok) throw new Error("Failed to advance market");
    const data = await res.json();
    state.stocks = data.market.stocks;
    state.marketSummary = data.market.summary;
    state.portfolio = data.portfolio;
    renderAll();
  } catch (err) {
    console.error("Tick error:", err);
  }
}

// ==========================================================================
// RENDER COORDINATOR
// ==========================================================================
function renderAll() {
  renderTickerTape();
  renderKpiCards();
  renderUserNav();
  renderMarketScreener();
  renderHoldingsTable();
  renderAssetAllocation();
  renderTransactionLedger();

  if (state.activeChartTab === "performance") {
    renderPortfolioPerformanceChart();
  } else {
    renderStockPriceChart();
  }
}

// ==========================================================================
// TICKER TAPE
// ==========================================================================
function renderTickerTape() {
  const track = document.getElementById("tickerTapeTrack");
  if (!track || !state.stocks.length) return;

  const html = state.stocks
    .map((s) => {
      const isUp = s.change >= 0;
      const arrow = isUp ? "▲" : "▼";
      const cls = isUp ? "up" : "down";
      return `
        <span class="ticker-item" onclick="selectStock('${s.symbol}')">
          <span class="ticker-symbol">${s.symbol}</span>
          <span class="ticker-price">$${s.price.toFixed(2)}</span>
          <span class="ticker-change ${cls}">${arrow} ${Math.abs(s.change_percent).toFixed(2)}%</span>
        </span>
      `;
    })
    .join("");

  // Duplicate for seamless infinite marquee loop
  track.innerHTML = html + html;
}

// ==========================================================================
// KPI STATS CARDS & HEADER
// ==========================================================================
function renderKpiCards() {
  if (!state.portfolio) return;

  const p = state.portfolio;
  const netWorthEl = document.getElementById("kpiNetWorth");
  const pnlEl = document.getElementById("kpiAllTimePnl");
  const cashEl = document.getElementById("kpiCash");
  const cashWeightEl = document.getElementById("kpiCashWeight");
  const stocksValEl = document.getElementById("kpiStocksVal");
  const unrealizedEl = document.getElementById("kpiUnrealizedPnl");
  const holdingsCountEl = document.getElementById("kpiHoldingsCount");
  const realizedEl = document.getElementById("kpiRealizedPnl");
  const txCountEl = document.getElementById("kpiTxCount");
  const indexEl = document.getElementById("kpiMarketIndex");
  const tickCounterEl = document.getElementById("kpiTickCounter");
  const netWorthBadge = document.getElementById("kpiNetWorthBadge");

  netWorthEl.textContent = formatCurrency(p.total_net_worth);
  
  const isProfit = p.total_pnl >= 0;
  pnlEl.textContent = `All-time P&L: ${isProfit ? "+" : ""}${formatCurrency(p.total_pnl)} (${isProfit ? "+" : ""}${p.total_return_pct.toFixed(2)}%)`;
  pnlEl.className = "kpi-subtext " + (isProfit ? "text-success" : "text-danger");

  netWorthBadge.className = "kpi-badge " + (isProfit ? "positive" : "negative");
  netWorthBadge.textContent = `${isProfit ? "+" : ""}${p.total_return_pct.toFixed(2)}%`;

  cashEl.textContent = formatCurrency(p.cash);
  const cashWeight = p.total_net_worth > 0 ? (p.cash / p.total_net_worth * 100).toFixed(1) : "100.0";
  cashWeightEl.textContent = `${cashWeight}% of portfolio`;

  stocksValEl.textContent = formatCurrency(p.stocks_value);
  const isUnrealizedProfit = p.unrealized_pnl >= 0;
  unrealizedEl.textContent = `Unrealized: ${isUnrealizedProfit ? "+" : ""}${formatCurrency(p.unrealized_pnl)}`;
  unrealizedEl.className = "kpi-subtext " + (isUnrealizedProfit ? "text-success" : "text-danger");
  holdingsCountEl.textContent = `${p.holdings_count} Assets`;

  const isRealizedProfit = p.realized_pnl >= 0;
  realizedEl.textContent = `${isRealizedProfit ? "+" : ""}${formatCurrency(p.realized_pnl)}`;
  realizedEl.className = "kpi-value font-mono " + (isRealizedProfit ? "text-success" : "text-danger");
  txCountEl.textContent = `${p.transactions_count} Transactions`;

  const idxChg = state.marketSummary.market_index_change_percent || 0;
  const isIdxUp = idxChg >= 0;
  indexEl.textContent = `${isIdxUp ? "+" : ""}${idxChg.toFixed(2)}%`;
  indexEl.className = "kpi-value font-mono " + (isIdxUp ? "text-success" : "text-danger");
  tickCounterEl.textContent = `Ticks: ${state.marketSummary.tick_count || 0} | Vol: ${(state.marketSummary.total_volume || 0).toLocaleString()}`;
}

function renderUserNav() {
  if (!state.portfolio || !state.portfolio.user) return;
  const u = state.portfolio.user;
  document.getElementById("userDisplayName").textContent = u.display_name || u.username;
  document.getElementById("userNavCash").textContent = formatCurrency(state.portfolio.cash);
  document.getElementById("userAvatar").textContent = (u.display_name || u.username).charAt(0).toUpperCase();
}

// ==========================================================================
// ASSET ALLOCATION BAR & LEGEND
// ==========================================================================
function renderAssetAllocation() {
  if (!state.portfolio || !state.portfolio.asset_allocation) return;

  const bar = document.getElementById("allocationBar");
  const legend = document.getElementById("allocationLegend");
  const subtitle = document.getElementById("holdingsSubtitle");
  const alloc = state.portfolio.asset_allocation;

  subtitle.textContent = `${state.portfolio.holdings_count} positions held | ${formatCurrency(state.portfolio.stocks_value)} invested`;

  bar.innerHTML = alloc
    .map(
      (a) => `<div class="allocation-segment" style="width: ${a.percentage}%; background-color: ${a.color};" title="${a.label}: ${a.percentage}% (${formatCurrency(a.value)})"></div>`
    )
    .join("");

  legend.innerHTML = alloc
    .map(
      (a) => `
      <div class="legend-item">
        <span class="legend-dot" style="background-color: ${a.color};"></span>
        <span>${a.label} (${a.percentage}%)</span>
      </div>
    `
    )
    .join("");
}

// ==========================================================================
// HOLDINGS TABLE
// ==========================================================================
function renderHoldingsTable() {
  const tbody = document.getElementById("holdingsTableBody");
  if (!state.portfolio) return;

  const holdings = state.portfolio.holdings || [];
  if (holdings.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center empty-state">No open positions. Buy stocks from the market screener!</td></tr>`;
    return;
  }

  tbody.innerHTML = holdings
    .map((h) => {
      const isUp = h.unrealized_pnl >= 0;
      const pnlColorClass = isUp ? "text-success" : "text-danger";
      const pnlPrefix = isUp ? "+" : "";

      return `
        <tr>
          <td>
            <div style="cursor: pointer;" onclick="selectStock('${h.symbol}')">
              <span class="font-bold" style="color: var(--color-accent);">${h.symbol}</span>
              <div style="font-size: 0.72rem; color: var(--text-dim);">${h.name}</div>
            </div>
          </td>
          <td class="text-right font-mono">${h.quantity.toLocaleString()}</td>
          <td class="text-right font-mono">$${h.average_cost.toFixed(2)}</td>
          <td class="text-right font-mono font-bold">$${h.current_price.toFixed(2)}</td>
          <td class="text-right font-mono font-bold">$${h.current_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
          <td class="text-right font-mono ${pnlColorClass}">
            ${pnlPrefix}$${h.unrealized_pnl.toFixed(2)}
            <span style="font-size: 0.72rem;">(${pnlPrefix}${h.unrealized_pnl_percent.toFixed(2)}%)</span>
          </td>
          <td class="text-right font-mono">${h.portfolio_weight.toFixed(1)}%</td>
          <td class="text-center">
            <button class="btn btn-buy btn-sm" onclick="openTradeModal('${h.symbol}', 'BUY')" style="padding: 2px 8px; font-size: 0.7rem; margin-right: 4px;">Buy</button>
            <button class="btn btn-sell btn-sm" onclick="openTradeModal('${h.symbol}', 'SELL')" style="padding: 2px 8px; font-size: 0.7rem;">Sell</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

// ==========================================================================
// MARKET SCREENER
// ==========================================================================
function renderMarketScreener() {
  const container = document.getElementById("stockListContainer");
  const countEl = document.getElementById("marketTickerCount");
  if (!container || !state.stocks.length) return;

  const watchlist = (state.portfolio && state.portfolio.user && state.portfolio.user.watchlist) || [];

  // Filter stocks based on search and sector
  let filtered = state.stocks.filter((s) => {
    const matchesSearch =
      s.symbol.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
      s.name.toLowerCase().includes(state.searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (state.selectedSector === "ALL") return true;
    if (state.selectedSector === "WATCHLIST") return watchlist.includes(s.symbol);
    return s.sector === state.selectedSector;
  });

  countEl.textContent = `${filtered.length} Stocks Listed`;

  container.innerHTML = filtered
    .map((s) => {
      const isUp = s.change >= 0;
      const arrow = isUp ? "▲" : "▼";
      const changeClass = isUp ? "text-success" : "text-danger";
      const isFavorite = watchlist.includes(s.symbol);
      const isSelected = s.symbol === state.selectedStockSymbol;

      return `
        <div class="stock-card ${isSelected ? "active-selected" : ""}" onclick="selectStock('${s.symbol}')">
          <div class="card-left">
            <span class="card-star ${isFavorite ? "active" : ""}" onclick="event.stopPropagation(); toggleWatchlist('${s.symbol}')">★</span>
            <div class="card-info">
              <span class="card-symbol">${s.symbol}</span>
              <span class="card-name" title="${s.name}">${s.name}</span>
            </div>
          </div>
          <div class="card-right">
            <div class="card-pricing">
              <span class="card-price">$${s.price.toFixed(2)}</span>
              <span class="card-change ${changeClass}">${arrow} ${Math.abs(s.change_percent).toFixed(2)}%</span>
            </div>
            <div class="card-actions" onclick="event.stopPropagation();">
              <button class="btn btn-buy btn-sm" onclick="openTradeModal('${s.symbol}', 'BUY')" style="padding: 2px 7px; font-size: 0.7rem;">Buy</button>
              <button class="btn btn-sell btn-sm" onclick="openTradeModal('${s.symbol}', 'SELL')" style="padding: 2px 7px; font-size: 0.7rem;">Sell</button>
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

function selectStock(symbol) {
  state.selectedStockSymbol = symbol;
  
  // Switch to Stock Chart tab
  setChartTab("stock");
  renderMarketScreener();
  renderStockPriceChart();
}

async function toggleWatchlist(symbol) {
  try {
    const res = await fetch("/api/watchlist/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol }),
    });
    const data = await res.json();
    if (state.portfolio && state.portfolio.user) {
      state.portfolio.user.watchlist = data.watchlist;
    }
    renderMarketScreener();
    showToast(`${symbol} ${data.in_watchlist ? "added to" : "removed from"} Watchlist`, "info");
  } catch (err) {
    showToast("Error updating watchlist", "error");
  }
}

// ==========================================================================
// TRANSACTION AUDIT LEDGER
// ==========================================================================
function renderTransactionLedger() {
  const tbody = document.getElementById("txTableBody");
  const subtitle = document.getElementById("txCountSubtitle");
  if (!state.portfolio) return;

  const txs = state.portfolio.transactions || [];
  subtitle.textContent = `${state.portfolio.transactions_count || txs.length} executed trades`;

  if (!txs || txs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center empty-state">No transaction history yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = txs
    .slice()
    .reverse()
    .map((t) => {
      const isBuy = t.transaction_type === "BUY";
      const badgeCls = isBuy ? "badge-buy" : "badge-sell";

      return `
        <tr>
          <td class="font-mono" style="color: var(--text-dim);">${t.id}</td>
          <td style="color: var(--text-muted); font-size: 0.75rem;">${t.timestamp}</td>
          <td><span class="badge-tag ${badgeCls}">${t.transaction_type}</span></td>
          <td class="font-bold" style="color: var(--color-accent);">${t.symbol}</td>
          <td class="text-right font-mono">${t.quantity.toLocaleString()}</td>
          <td class="text-right font-mono">$${t.price_per_share.toFixed(2)}</td>
          <td class="text-right font-mono font-bold">$${t.total_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
        </tr>
      `;
    })
    .join("");
}

// ==========================================================================
// HIGH-PERFORMANCE CANVAS CHARTING ENGINES
// ==========================================================================

/**
 * 1. PORTFOLIO PERFORMANCE OVER TIME CHART
 */
function renderPortfolioPerformanceChart() {
  const canvas = document.getElementById("portfolioChartCanvas");
  if (!canvas || !state.portfolio) return;

  const history = state.portfolio.performance_history || [];
  if (history.length < 2) return;

  // Setup HiDPI Canvas
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const width = rect.width;
  const height = rect.height;
  const padding = { top: 20, right: 30, bottom: 35, left: 70 };

  // Calculate bounds
  const values = history.map((h) => h.total_value);
  const minVal = Math.min(...values, state.portfolio.initial_cash * 0.98);
  const maxVal = Math.max(...values, state.portfolio.initial_cash * 1.02);
  const valRange = maxVal - minVal || 1;

  ctx.clearRect(0, 0, width, height);

  // Draw Grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
  ctx.lineWidth = 1;
  const gridSteps = 4;
  for (let i = 0; i <= gridSteps; i++) {
    const y = padding.top + (height - padding.top - padding.bottom) * (i / gridSteps);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();

    // Axis label
    const valLabel = maxVal - (valRange * (i / gridSteps));
    ctx.fillStyle = "#64748b";
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "right";
    ctx.fillText("$" + Math.round(valLabel).toLocaleString(), padding.left - 10, y + 3);
  }

  // Draw Initial Cash Benchmark Line (Baseline)
  const baselineY = padding.top + (height - padding.top - padding.bottom) * (1 - (state.portfolio.initial_cash - minVal) / valRange);
  ctx.save();
  ctx.setLineDash([4, 4]);
  ctx.strokeStyle = "rgba(245, 158, 11, 0.4)";
  ctx.beginPath();
  ctx.moveTo(padding.left, baselineY);
  ctx.lineTo(width - padding.right, baselineY);
  ctx.stroke();
  ctx.fillStyle = "rgba(245, 158, 11, 0.7)";
  ctx.textAlign = "left";
  ctx.font = "9px Inter, sans-serif";
  ctx.fillText("Initial Capital ($" + state.portfolio.initial_cash.toLocaleString() + ")", padding.left + 5, baselineY - 4);
  ctx.restore();

  // Coordinates of points
  const points = history.map((item, idx) => {
    const x = padding.left + ((width - padding.left - padding.right) * idx) / (history.length - 1);
    const y = padding.top + (height - padding.top - padding.bottom) * (1 - (item.total_value - minVal) / valRange);
    return { x, y, data: item };
  });

  // Area Gradient
  const isUp = history[history.length - 1].total_value >= state.portfolio.initial_cash;
  const strokeColor = isUp ? "#00f59b" : "#ff4365";
  const grad = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
  grad.addColorStop(0, isUp ? "rgba(0, 245, 155, 0.28)" : "rgba(255, 67, 101, 0.28)");
  grad.addColorStop(1, "rgba(0, 0, 0, 0.0)");

  // Draw Area Path
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    const xc = (points[i - 1].x + points[i].x) / 2;
    const yc = (points[i - 1].y + points[i].y) / 2;
    ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, xc, yc);
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
  ctx.lineTo(points[points.length - 1].x, height - padding.bottom);
  ctx.lineTo(points[0].x, height - padding.bottom);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Draw Stroke Path
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    const xc = (points[i - 1].x + points[i].x) / 2;
    const yc = (points[i - 1].y + points[i].y) / 2;
    ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, xc, yc);
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Draw End Point Dot
  const lastPt = points[points.length - 1];
  ctx.beginPath();
  ctx.arc(lastPt.x, lastPt.y, 4, 0, Math.PI * 2);
  ctx.fillStyle = strokeColor;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#fff";
  ctx.stroke();

  // Update Header Metric Chips
  const startCashEl = document.getElementById("perfStartCash");
  const curWorthEl = document.getElementById("perfCurWorth");
  const netPnlEl = document.getElementById("perfNetPnl");
  if (startCashEl) startCashEl.textContent = formatCurrency(state.portfolio.initial_cash);
  if (curWorthEl) curWorthEl.textContent = formatCurrency(state.portfolio.total_net_worth);
  if (netPnlEl) {
    const pnl = state.portfolio.total_pnl;
    const pct = state.portfolio.total_return_pct;
    netPnlEl.textContent = `${pnl >= 0 ? "+" : ""}${formatCurrency(pnl)} (${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%)`;
    netPnlEl.className = "chip-val font-mono " + (pnl >= 0 ? "text-success" : "text-danger");
  }

  // Attach Mouse Tooltip Listener
  setupCanvasTooltip(canvas, points, "perfTooltip", (pt) => {
    return `<strong>${pt.data.timestamp}</strong><br>Net Worth: ${formatCurrency(pt.data.total_value)}<br>Unrealized: ${formatCurrency(pt.data.unrealized_pnl)}`;
  });
}

/**
 * 2. LIVE STOCK CANDLESTICK / PRICE HISTORY CHART
 */
function renderStockPriceChart() {
  const canvas = document.getElementById("stockChartCanvas");
  if (!canvas) return;

  const stock = state.stocks.find((s) => s.symbol === state.selectedStockSymbol);
  if (!stock) return;

  const history = stock.history || [];
  if (history.length < 2) return;

  // Update Stock Chart Header
  document.getElementById("activeChartSymbol").textContent = stock.symbol;
  document.getElementById("stockChartSym").textContent = stock.symbol;
  document.getElementById("stockChartName").textContent = stock.name;
  document.getElementById("stockChartPrice").textContent = `$${stock.price.toFixed(2)}`;
  
  const isUp = stock.change >= 0;
  const chgEl = document.getElementById("stockChartChange");
  chgEl.textContent = `${isUp ? "+" : ""}${stock.change.toFixed(2)} (${isUp ? "+" : ""}${stock.change_percent.toFixed(2)}%)`;
  chgEl.className = "stock-active-change font-mono " + (isUp ? "text-success" : "text-danger");

  // Setup HiDPI Canvas
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const width = rect.width;
  const height = rect.height;
  const padding = { top: 20, right: 30, bottom: 40, left: 60 };

  const prices = history.map((h) => h.price);
  const minPrice = Math.min(...prices) * 0.995;
  const maxPrice = Math.max(...prices) * 1.005;
  const priceRange = maxPrice - minPrice || 1;

  ctx.clearRect(0, 0, width, height);

  // Draw Grid Lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
  ctx.lineWidth = 1;
  const gridSteps = 4;
  for (let i = 0; i <= gridSteps; i++) {
    const y = padding.top + (height - padding.top - padding.bottom) * (i / gridSteps);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();

    const pLabel = maxPrice - (priceRange * (i / gridSteps));
    ctx.fillStyle = "#64748b";
    ctx.font = "10px JetBrains Mono, monospace";
    ctx.textAlign = "right";
    ctx.fillText("$" + pLabel.toFixed(2), padding.left - 10, y + 3);
  }

  // Points mapping
  const points = history.map((item, idx) => {
    const x = padding.left + ((width - padding.left - padding.right) * idx) / (history.length - 1);
    const y = padding.top + (height - padding.top - padding.bottom) * (1 - (item.price - minPrice) / priceRange);
    return { x, y, data: item };
  });

  // Area Fill
  const strokeColor = isUp ? "#00f59b" : "#ff4365";
  const grad = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
  grad.addColorStop(0, isUp ? "rgba(0, 245, 155, 0.25)" : "rgba(255, 67, 101, 0.25)");
  grad.addColorStop(1, "rgba(0, 0, 0, 0.0)");

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    const xc = (points[i - 1].x + points[i].x) / 2;
    const yc = (points[i - 1].y + points[i].y) / 2;
    ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, xc, yc);
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
  ctx.lineTo(points[points.length - 1].x, height - padding.bottom);
  ctx.lineTo(points[0].x, height - padding.bottom);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Stroke Line
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    const xc = (points[i - 1].x + points[i].x) / 2;
    const yc = (points[i - 1].y + points[i].y) / 2;
    ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, xc, yc);
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Draw End Point Dot
  const lastPt = points[points.length - 1];
  ctx.beginPath();
  ctx.arc(lastPt.x, lastPt.y, 4, 0, Math.PI * 2);
  ctx.fillStyle = strokeColor;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#fff";
  ctx.stroke();

  // Attach Mouse Tooltip Listener
  setupCanvasTooltip(canvas, points, "stockTooltip", (pt) => {
    return `<strong>${pt.data.timestamp}</strong><br>Price: $${pt.data.price.toFixed(2)}<br>Vol: ${(pt.data.volume || 0).toLocaleString()}`;
  });
}

function setupCanvasTooltip(canvas, points, tooltipId, formatFn) {
  const tooltip = document.getElementById(tooltipId);
  if (!tooltip) return;

  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    
    // Find closest point
    let closest = points[0];
    let minDist = Math.abs(points[0].x - mouseX);
    for (let i = 1; i < points.length; i++) {
      const dist = Math.abs(points[i].x - mouseX);
      if (dist < minDist) {
        minDist = dist;
        closest = points[i];
      }
    }

    if (minDist < 40) {
      tooltip.style.display = "block";
      tooltip.style.left = `${closest.x + 10}px`;
      tooltip.style.top = `${closest.y - 45}px`;
      tooltip.innerHTML = formatFn(closest);
    } else {
      tooltip.style.display = "none";
    }
  };

  canvas.onmouseleave = () => {
    tooltip.style.display = "none";
  };
}

// ==========================================================================
// TRADE ORDER MODAL & EXECUTION
// ==========================================================================
function openTradeModal(symbol, type = "BUY") {
  const stock = state.stocks.find((s) => s.symbol === symbol.toUpperCase());
  if (!stock) {
    showToast("Stock ticker not found", "error");
    return;
  }

  state.tradeStock = stock;
  state.activeTradeType = type.toUpperCase();

  document.getElementById("modalStockTitle").textContent = `${stock.symbol} - ${stock.name}`;
  document.getElementById("modalPrice").textContent = `$${stock.price.toFixed(2)}`;
  document.getElementById("modalAvailableCash").textContent = formatCurrency(state.portfolio.cash);

  const owned = (state.portfolio.holdings || []).find((h) => h.symbol === stock.symbol);
  const ownedShares = owned ? owned.quantity : 0;
  document.getElementById("modalOwnedShares").textContent = `${ownedShares.toLocaleString()} shares`;

  setTradeType(state.activeTradeType);

  document.getElementById("tradeModalBackdrop").classList.add("open");
}

function closeTradeModal() {
  document.getElementById("tradeModalBackdrop").classList.remove("open");
  document.getElementById("modalErrorMsg").style.display = "none";
}

function setTradeType(type) {
  state.activeTradeType = type;
  const isBuy = type === "BUY";

  const btnBuy = document.getElementById("btnToggleBuy");
  const btnSell = document.getElementById("btnToggleSell");
  const modalTag = document.getElementById("modalTradeType");
  const confirmBtn = document.getElementById("modalConfirmBtn");

  if (isBuy) {
    btnBuy.classList.add("active");
    btnSell.classList.remove("active");
    modalTag.textContent = "BUY ORDER";
    modalTag.style.background = "var(--color-bull-bg)";
    modalTag.style.color = "var(--color-bull)";
    confirmBtn.textContent = `Confirm Buy Order (${state.tradeStock.symbol})`;
    confirmBtn.className = "btn btn-buy-confirm";
  } else {
    btnSell.classList.add("active");
    btnBuy.classList.remove("active");
    modalTag.textContent = "SELL ORDER";
    modalTag.style.background = "var(--color-bear-bg)";
    modalTag.style.color = "var(--color-bear)";
    confirmBtn.textContent = `Confirm Sell Order (${state.tradeStock.symbol})`;
    confirmBtn.className = "btn btn-sell";
  }

  updateMaxShares();
  calculateOrderReceipt();
}

function updateMaxShares() {
  if (!state.tradeStock || !state.portfolio) return;

  const sharesInput = document.getElementById("orderSharesInput");
  const slider = document.getElementById("orderSharesSlider");
  const maxLabel = document.getElementById("modalMaxSharesLabel");

  let max = 0;
  if (state.activeTradeType === "BUY") {
    max = Math.floor(state.portfolio.cash / state.tradeStock.price);
  } else {
    const owned = (state.portfolio.holdings || []).find((h) => h.symbol === state.tradeStock.symbol);
    max = owned ? owned.quantity : 0;
  }

  maxLabel.textContent = `Max: ${max.toLocaleString()}`;
  slider.max = Math.max(1, max);

  let currentVal = parseInt(sharesInput.value, 10) || 1;
  if (currentVal > max && max > 0) {
    sharesInput.value = max;
    slider.value = max;
  } else if (max === 0) {
    sharesInput.value = 0;
    slider.value = 0;
  }
}

function calculateOrderReceipt() {
  if (!state.tradeStock) return;

  const sharesInput = document.getElementById("orderSharesInput");
  const qty = parseInt(sharesInput.value, 10) || 0;
  const price = state.tradeStock.price;
  const total = qty * price;

  document.getElementById("modalEstimatedCost").textContent = formatCurrency(total);
  document.getElementById("modalTotalCost").textContent = formatCurrency(total);

  const errorEl = document.getElementById("modalErrorMsg");
  errorEl.style.display = "none";

  if (state.activeTradeType === "BUY") {
    if (total > state.portfolio.cash) {
      errorEl.textContent = `Insufficient cash! Available: ${formatCurrency(state.portfolio.cash)}`;
      errorEl.style.display = "block";
    }
  } else {
    const owned = (state.portfolio.holdings || []).find((h) => h.symbol === state.tradeStock.symbol);
    const ownedQty = owned ? owned.quantity : 0;
    if (qty > ownedQty) {
      errorEl.textContent = `Insufficient shares! You own ${ownedQty} shares.`;
      errorEl.style.display = "block";
    }
  }
}

async function executeTrade() {
  const sharesInput = document.getElementById("orderSharesInput");
  const quantity = parseInt(sharesInput.value, 10);
  const symbol = state.tradeStock.symbol;
  const endpoint = state.activeTradeType === "BUY" ? "/api/trade/buy" : "/api/trade/sell";

  if (!quantity || quantity <= 0) {
    showToast("Quantity must be greater than zero", "error");
    return;
  }

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, quantity }),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast(data.message || "Trade execution failed", "error");
      return;
    }

    state.portfolio = data.portfolio;
    showToast(data.message, "success");
    closeTradeModal();
    renderAll();
  } catch (err) {
    showToast("Trade error: " + err.message, "error");
  }
}

// ==========================================================================
// SIMULATION & CONTROLS
// ==========================================================================
function startAutoTick() {
  if (state.autoTickIntervalId) clearInterval(state.autoTickIntervalId);
  state.autoTickIntervalId = setInterval(() => {
    if (state.autoTickEnabled) {
      triggerTick(1);
    }
  }, state.tickSpeed);
}

function toggleAutoTick() {
  state.autoTickEnabled = !state.autoTickEnabled;
  const btn = document.getElementById("btnAutoTick");
  const icon = document.getElementById("playPauseIcon");
  const txt = document.getElementById("playPauseText");
  const pulse = document.getElementById("marketPulse");
  const statusTxt = document.getElementById("marketStatusText");

  if (state.autoTickEnabled) {
    btn.classList.add("active");
    icon.textContent = "⏸";
    txt.textContent = "Auto-Tick";
    pulse.classList.add("live");
    statusTxt.textContent = "LIVE SIMULATION";
    showToast("Auto-tick resumed", "info");
  } else {
    btn.classList.remove("active");
    icon.textContent = "▶";
    txt.textContent = "Paused";
    pulse.classList.remove("live");
    statusTxt.textContent = "PAUSED";
    showToast("Auto-tick paused", "info");
  }
}

async function updateMarketSentiment(sentiment) {
  try {
    const res = await fetch("/api/market/sentiment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sentiment }),
    });
    const data = await res.json();
    showToast(`Market regime shifted to: ${data.label}`, "info");
  } catch (err) {
    showToast("Failed to change sentiment", "error");
  }
}

function setChartTab(tab) {
  state.activeChartTab = tab;
  const tabPerf = document.getElementById("tabPerfChart");
  const tabStock = document.getElementById("tabStockChart");
  const viewPerf = document.getElementById("viewPerfChart");
  const viewStock = document.getElementById("viewStockChart");

  if (tab === "performance") {
    tabPerf.classList.add("active");
    tabStock.classList.remove("active");
    viewPerf.classList.add("active");
    viewStock.classList.remove("active");
    renderPortfolioPerformanceChart();
  } else {
    tabStock.classList.add("active");
    tabPerf.classList.remove("active");
    viewStock.classList.add("active");
    viewPerf.classList.remove("active");
    renderStockPriceChart();
  }
}

// ==========================================================================
// EVENT LISTENERS & MODAL BINDINGS
// ==========================================================================
function initEventListeners() {
  // Chart Tabs
  document.getElementById("tabPerfChart").addEventListener("click", () => setChartTab("performance"));
  document.getElementById("tabStockChart").addEventListener("click", () => setChartTab("stock"));

  // Simulation Controls
  document.getElementById("btnAutoTick").addEventListener("click", toggleAutoTick);
  document.getElementById("btnStepTick").addEventListener("click", () => triggerTick(1));
  document.getElementById("sentimentSelect").addEventListener("change", (e) => updateMarketSentiment(e.target.value));
  document.getElementById("speedSelect").addEventListener("change", (e) => {
    state.tickSpeed = parseInt(e.target.value, 10);
    startAutoTick();
    showToast(`Simulation tick rate: ${state.tickSpeed / 1000}s`, "info");
  });

  // Chart Quick Trade Buttons
  document.getElementById("btnQuickBuyFromChart").addEventListener("click", () => {
    openTradeModal(state.selectedStockSymbol, "BUY");
  });
  document.getElementById("btnQuickSellFromChart").addEventListener("click", () => {
    openTradeModal(state.selectedStockSymbol, "SELL");
  });

  // Trade Modal Controls
  document.getElementById("modalCloseBtn").addEventListener("click", closeTradeModal);
  document.getElementById("modalCancelBtn").addEventListener("click", closeTradeModal);
  document.getElementById("modalConfirmBtn").addEventListener("click", executeTrade);
  document.getElementById("btnToggleBuy").addEventListener("click", () => setTradeType("BUY"));
  document.getElementById("btnToggleSell").addEventListener("click", () => setTradeType("SELL"));

  const sharesInput = document.getElementById("orderSharesInput");
  const sharesSlider = document.getElementById("orderSharesSlider");

  sharesInput.addEventListener("input", () => {
    sharesSlider.value = sharesInput.value;
    calculateOrderReceipt();
  });

  sharesSlider.addEventListener("input", () => {
    sharesInput.value = sharesSlider.value;
    calculateOrderReceipt();
  });

  document.getElementById("btnQtyMinus").addEventListener("click", () => {
    let val = parseInt(sharesInput.value, 10) || 1;
    if (val > 1) {
      sharesInput.value = val - 1;
      sharesSlider.value = val - 1;
      calculateOrderReceipt();
    }
  });

  document.getElementById("btnQtyPlus").addEventListener("click", () => {
    let val = parseInt(sharesInput.value, 10) || 0;
    sharesInput.value = val + 1;
    sharesSlider.value = val + 1;
    calculateOrderReceipt();
  });

  document.getElementById("modalMaxSharesLabel").addEventListener("click", () => {
    let max = 0;
    if (state.activeTradeType === "BUY") {
      max = Math.floor(state.portfolio.cash / state.tradeStock.price);
    } else {
      const owned = (state.portfolio.holdings || []).find((h) => h.symbol === state.tradeStock.symbol);
      max = owned ? owned.quantity : 0;
    }
    sharesInput.value = max;
    sharesSlider.value = max;
    calculateOrderReceipt();
  });

  // Search & Filter
  document.getElementById("stockSearchInput").addEventListener("input", (e) => {
    state.searchQuery = e.target.value;
    renderMarketScreener();
  });

  document.querySelectorAll("#sectorFilterPills .pill").forEach((pill) => {
    pill.addEventListener("click", (e) => {
      document.querySelectorAll("#sectorFilterPills .pill").forEach((p) => p.classList.remove("active"));
      e.target.classList.add("active");
      state.selectedSector = e.target.dataset.sector;
      renderMarketScreener();
    });
  });

  // Deposit Funds Modal
  const depositModal = document.getElementById("depositModalBackdrop");
  document.getElementById("btnDeposit").addEventListener("click", () => depositModal.classList.add("open"));
  document.getElementById("depositModalCloseBtn").addEventListener("click", () => depositModal.classList.remove("open"));
  document.getElementById("depositCancelBtn").addEventListener("click", () => depositModal.classList.remove("open"));

  document.querySelectorAll(".quick-amounts .pill").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      document.getElementById("depositAmountInput").value = e.target.dataset.amount;
    });
  });

  document.getElementById("depositConfirmBtn").addEventListener("click", async () => {
    const amt = parseFloat(document.getElementById("depositAmountInput").value);
    if (!amt || amt <= 0) {
      showToast("Please enter a valid deposit amount", "error");
      return;
    }
    try {
      const res = await fetch("/api/user/deposit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: amt }),
      });
      const data = await res.json();
      state.portfolio = data.portfolio;
      showToast(data.message, "success");
      depositModal.classList.remove("open");
      renderAll();
    } catch (err) {
      showToast("Deposit error: " + err.message, "error");
    }
  });

  // Switch User Modal
  const userModal = document.getElementById("userModalBackdrop");
  document.getElementById("userPillBtn").addEventListener("click", () => userModal.classList.add("open"));
  document.getElementById("userModalCloseBtn").addEventListener("click", () => userModal.classList.remove("open"));
  document.getElementById("userCancelBtn").addEventListener("click", () => userModal.classList.remove("open"));

  document.getElementById("userConfirmBtn").addEventListener("click", async () => {
    const uname = document.getElementById("switchUsernameInput").value.trim();
    const dname = document.getElementById("switchDisplayNameInput").value.trim();
    if (!uname) {
      showToast("Username required", "error");
      return;
    }
    try {
      const res = await fetch("/api/user/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: uname, display_name: dname }),
      });
      const data = await res.json();
      state.portfolio = data.portfolio;
      showToast(data.message, "success");
      userModal.classList.remove("open");
      renderAll();
    } catch (err) {
      showToast("User switch error: " + err.message, "error");
    }
  });

  // Export & Import
  document.getElementById("btnExport").addEventListener("click", () => {
    window.location.href = "/api/export";
    showToast("Portfolio export started...", "info");
  });

  const importFileInput = document.getElementById("importFileInput");
  importFileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/import", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        showToast(data.message || "Failed to import portfolio", "error");
        return;
      }
      state.portfolio = data.portfolio;
      showToast("Portfolio successfully imported!", "success");
      renderAll();
    } catch (err) {
      showToast("Import error: " + err.message, "error");
    }
    importFileInput.value = "";
  });
}

// ==========================================================================
// UTILITY HELPERS
// ==========================================================================
function formatCurrency(val) {
  if (val === undefined || val === null) return "$0.00";
  return "$" + Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const icon = type === "success" ? "✔" : type === "error" ? "✘" : "ℹ";
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
