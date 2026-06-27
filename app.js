"use strict";

const DATA_FILES = {
  predictions: "data/voorspellingen.csv",
  columns: "data/kolommen.csv",
  results: "data/uitslagen.csv",
  worstThirds: "data/slechtste_nummers_drie.csv",
};

const WORST_THIRD_FIELDS = [
  "slechtste_3_1",
  "slechtste_3_2",
  "slechtste_3_3",
  "slechtste_3_4",
];

// Oude CSV-bestanden blijven werken, zodat een bestaande import niet direct stukgaat.
const LEGACY_WORST_THIRD_FIELDS = ["bonus_a1", "bonus_a2", "bonus_a3", "bonus_a4"];

const BONUS_FIELDS = [
  { key: "bonus_finale", label: "Finale en wereldkampioen" },
  { key: "bonus_topscorer", label: "Topscorer en doelpunten" },
  { key: "bonus_kaarten", label: "Aantal gele/rode kaarten" },
  { key: "bonus_trump", label: "Trump doet de aftrap bij" },
  {
    key: "bonus_meeste_kaarten",
    fallbackKeys: ["bonus_kaartenland"],
    label: "Land met de meeste kaarten"
  },
  { key: "bonus_weghorst", label: "Speelminuten Wout Weghorst" },
];

const state = {
  predictions: [],
  columns: [],
  resultsByPool: new Map(),
  actualWorstThirds: new Map(),
  worstThirdsComplete: false,
  ranking: [],
  selectedName: null,
  availablePoints: 0,
  completedPools: 0,
};

const elements = {
  loadStatus: document.querySelector("#load-status"),
  livePill: document.querySelector(".live-pill"),
  errorPanel: document.querySelector("#error-panel"),
  warningPanel: document.querySelector("#warning-panel"),
  participantCount: document.querySelector("#participant-count"),
  completedPools: document.querySelector("#completed-pools"),
  availablePoints: document.querySelector("#available-points"),
  lastUpdated: document.querySelector("#last-updated"),
  rankingBody: document.querySelector("#ranking-body"),
  searchInput: document.querySelector("#search-input"),
  emptySearch: document.querySelector("#empty-search"),
  participantSection: document.querySelector("#participant-section"),
  participantTitle: document.querySelector("#participant-title"),
  participantSummary: document.querySelector("#participant-summary"),
  poolDetails: document.querySelector("#pool-details"),
  worstThirdsDetails: document.querySelector("#worst-thirds-details"),
  bonusDetails: document.querySelector("#bonus-details"),
  closeDetails: document.querySelector("#close-details"),
};

function parseCsv(text) {
  const source = text.replace(/^\uFEFF/, "");
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];

    if (quoted) {
      if (char === '"' && next === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }

  if (field !== "" || row.length) {
    row.push(field.replace(/\r$/, ""));
    if (row.some((value) => value !== "")) rows.push(row);
  }

  if (!rows.length) return [];
  const headers = rows[0].map((header) => header.trim());
  return rows.slice(1).map((values) => Object.fromEntries(
    headers.map((header, index) => [header, (values[index] ?? "").trim()]),
  ));
}

async function loadCsv(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} kon niet worden geladen (${response.status}).`);
  return parseCsv(await response.text());
}

function normalize(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("nl-NL")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function groupedColumns() {
  const pools = new Map();
  for (const item of state.columns) {
    const pool = item.poule.toUpperCase();
    if (!pools.has(pool)) pools.set(pool, []);
    pools.get(pool).push(item);
  }
  return [...pools.entries()].sort(([a], [b]) => a.localeCompare(b, "nl"));
}

function teamLookup() {
  return new Map(state.columns.map((item) => [normalize(item.land), item.land]));
}

function getPredictedWorstThirds(participant) {
  const preferred = WORST_THIRD_FIELDS.map((key) => String(participant[key] ?? "").trim());
  if (preferred.some(Boolean)) return preferred.filter(Boolean);
  return LEGACY_WORST_THIRD_FIELDS
    .map((key) => String(participant[key] ?? "").trim())
    .filter(Boolean);
}

function prepareResults(rawResults) {
  const warnings = [];
  const byPool = new Map();
  const mappingByTeam = new Map(
    state.columns.map((item) => [`${item.poule.toUpperCase()}|${normalize(item.land)}`, item]),
  );

  for (const row of rawResults) {
    const pool = String(row.poule ?? "").trim().toUpperCase();
    const land = String(row.land ?? "").trim();
    const positionText = String(row.positie ?? "").trim();
    if (!pool && !land && !positionText) continue;
    if (!pool || !land) {
      warnings.push("Een regel in uitslagen.csv mist een poule of land.");
      continue;
    }

    const mapping = mappingByTeam.get(`${pool}|${normalize(land)}`);
    if (!mapping) {
      warnings.push(`Onbekend land in poule ${pool}: ${land}.`);
      continue;
    }

    if (!byPool.has(pool)) byPool.set(pool, { positions: new Map(), complete: false, errors: [] });
    const poolResult = byPool.get(pool);
    if (positionText === "") continue;

    const position = Number(positionText);
    if (!Number.isInteger(position) || position < 1 || position > 4) {
      poolResult.errors.push(`${land} heeft een ongeldige positie: ${positionText}.`);
      continue;
    }
    poolResult.positions.set(mapping.kolom, position);
  }

  for (const [pool, columns] of groupedColumns()) {
    if (!byPool.has(pool)) byPool.set(pool, { positions: new Map(), complete: false, errors: [] });
    const result = byPool.get(pool);
    const values = columns
      .map((column) => result.positions.get(column.kolom))
      .filter((value) => value !== undefined);

    if (values.length === 4 && new Set(values).size === 4 && values.every((value) => value >= 1 && value <= 4)) {
      result.complete = true;
    } else if (values.length > 0) {
      result.errors.push(`Poule ${pool} is nog niet compleet of bevat dubbele posities; deze poule telt nog niet mee.`);
    }

    warnings.push(...result.errors);
  }

  state.resultsByPool = byPool;
  return [...new Set(warnings)];
}

function prepareWorstThirds(rawRows) {
  const warnings = [];
  const lookup = teamLookup();
  const actual = new Map();
  let filledRows = 0;

  for (const row of rawRows) {
    const land = String(row.land ?? "").trim();
    if (!land) continue;
    filledRows += 1;
    const key = normalize(land);
    const canonical = lookup.get(key);
    if (!canonical) {
      warnings.push(`Onbekend land bij de slechtste nummers drie: ${land}.`);
      continue;
    }
    if (actual.has(key)) {
      warnings.push(`${canonical} staat dubbel in slechtste_nummers_drie.csv.`);
      continue;
    }
    actual.set(key, canonical);
  }

  state.actualWorstThirds = actual;
  state.worstThirdsComplete = actual.size === 4;

  if (filledRows > 0 && !state.worstThirdsComplete) {
    warnings.push("De vier slechtste nummers drie zijn nog niet compleet en tellen daarom nog niet mee.");
  }
  if (actual.size > 4) {
    warnings.push("Er mogen precies vier slechtste nummers drie worden ingevuld.");
    state.worstThirdsComplete = false;
  }

  return warnings;
}

function scoreParticipant(prediction) {
  let poolPositionScore = 0;
  let perfectPools = 0;
  const poolScores = new Map();

  for (const [pool, columns] of groupedColumns()) {
    const actual = state.resultsByPool.get(pool);
    if (!actual?.complete) {
      poolScores.set(pool, null);
      continue;
    }

    let poolScore = 0;
    for (const column of columns) {
      if (Number(prediction[column.kolom]) === actual.positions.get(column.kolom)) poolScore += 1;
    }
    if (poolScore === 4) perfectPools += 1;
    poolPositionScore += poolScore;
    poolScores.set(pool, poolScore);
  }

  const predictedWorstThirds = getPredictedWorstThirds(prediction);
  const uniquePredictions = new Map();
  for (const team of predictedWorstThirds) {
    const key = normalize(team);
    if (key && !uniquePredictions.has(key)) uniquePredictions.set(key, team);
  }

  const worstThirdHits = state.worstThirdsComplete
    ? [...uniquePredictions.keys()].filter((key) => state.actualWorstThirds.has(key))
    : [];
  const worstThirdScore = worstThirdHits.length * 3;
  const score = poolPositionScore + worstThirdScore;

  return {
    ...prediction,
    score,
    poolPositionScore,
    worstThirdScore,
    worstThirdHits,
    predictedWorstThirds,
    perfectPools,
    poolScores,
  };
}

function buildRanking() {
  state.completedPools = [...state.resultsByPool.values()].filter((result) => result.complete).length;
  state.availablePoints = state.completedPools * 4 + (state.worstThirdsComplete ? 12 : 0);
  state.ranking = state.predictions
    .map(scoreParticipant)
    .sort((a, b) => b.score - a.score
      || b.worstThirdScore - a.worstThirdScore
      || b.perfectPools - a.perfectPools
      || a.naam.localeCompare(b.naam, "nl"));
}

function rankForIndex(index) {
  if (index === 0) return 1;
  const current = state.ranking[index];
  const previous = state.ranking[index - 1];
  if (current.score === previous.score
    && current.worstThirdScore === previous.worstThirdScore
    && current.perfectPools === previous.perfectPools) {
    return rankForIndex(index - 1);
  }
  return index + 1;
}

function renderSummary() {
  elements.participantCount.textContent = String(state.predictions.length);
  elements.completedPools.textContent = String(state.completedPools);
  elements.availablePoints.textContent = String(state.availablePoints);
  elements.lastUpdated.textContent = new Intl.DateTimeFormat("nl-NL", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function renderRanking(filter = "") {
  const query = normalize(filter);
  const visible = state.ranking
    .map((participant, index) => ({ participant, rank: rankForIndex(index) }))
    .filter(({ participant }) => normalize(participant.naam).includes(query));

  elements.emptySearch.hidden = visible.length > 0;
  elements.rankingBody.innerHTML = visible.map(({ participant, rank }) => {
    const safeName = escapeHtml(participant.naam);
    const rankClass = rank <= 3 ? ` rank-badge--${rank}` : "";
    return `
      <tr>
        <td><span class="rank-badge${rankClass}">${rank}</span></td>
        <td><button class="name-button" type="button" data-name="${safeName}">${safeName}</button></td>
        <td class="number-column"><span class="score">${participant.score}</span> <span class="score-max">/ ${state.availablePoints}</span></td>
        <td class="number-column optional-column">${participant.perfectPools}</td>
        <td class="action-column"><button class="chevron" type="button" data-name="${safeName}" aria-label="Bekijk ${safeName}">›</button></td>
      </tr>`;
  }).join("");

  elements.rankingBody.querySelectorAll("[data-name]").forEach((button) => {
    button.addEventListener("click", () => selectParticipant(button.dataset.name));
  });
}

function renderWorstThirds(participant) {
  const predictions = participant.predictedWorstThirds;
  const actualTeams = [...state.actualWorstThirds.values()];
  const seenPredictions = new Set();
  const rows = Array.from({ length: 4 }, (_, index) => {
    const team = predictions[index] ?? "";
    const key = normalize(team);
    const isDuplicate = Boolean(key) && seenPredictions.has(key);
    if (key) seenPredictions.add(key);
    const isCorrect = state.worstThirdsComplete && !isDuplicate && state.actualWorstThirds.has(key);
    const status = !state.worstThirdsComplete
      ? '<span class="pending">Nog niet bekend</span>'
      : isDuplicate
        ? '<span class="position-wrong">Dubbel ingevuld</span>'
        : isCorrect
          ? '<span class="position-correct">Goed ✓</span>'
          : '<span class="position-wrong">Niet goed</span>';
    const points = !state.worstThirdsComplete ? "–" : isCorrect ? "3" : "0";
    return `
      <tr>
        <td>${index + 1}</td>
        <td>${team ? escapeHtml(team) : '<span class="pending">Niet ingevuld</span>'}</td>
        <td>${status}</td>
        <td class="number-column">${points}</td>
      </tr>`;
  }).join("");

  const actualBlock = state.worstThirdsComplete
    ? `<div class="actual-third-list"><span>Werkelijke vier:</span><div class="team-chips">${actualTeams.map((team) => `<span>${escapeHtml(team)}</span>`).join("")}</div></div>`
    : '<p class="phase-note">3 punten per land</p>';

  elements.worstThirdsDetails.innerHTML = `
    <div class="phase-extra-card">
      <div class="phase-extra-card__header">
        <div>
          <h3>Vier slechtste nummers drie</h3>
          <p>Onderdeel van fase 1 · 3 punten per correct land</p>
        </div>
        <span class="pool-points${state.worstThirdsComplete ? "" : " pool-points--pending"}">${state.worstThirdsComplete ? `${participant.worstThirdScore} / 12 punten` : "Nog niet gescoord"}</span>
      </div>
      <div class="table-wrap table-wrap--flat">
        <table class="worst-thirds-table">
          <thead><tr><th>#</th><th>Voorspeld land</th><th>Resultaat</th><th class="number-column">Punten</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      ${actualBlock}
    </div>`;
}

function renderBonus(participant) {
  elements.bonusDetails.innerHTML = BONUS_FIELDS.map((field) => {
    const value = String(participant[field.key] ?? "").trim();
    return `
      <article class="bonus-card">
        <span class="bonus-card__label">${escapeHtml(field.label)}</span>
        <p class="bonus-card__answer">${value ? escapeHtml(value) : "Niet ingevuld"}</p>
      </article>`;
  }).join("");
}

function renderParticipant(participant) {
  elements.participantTitle.textContent = participant.naam;
  elements.participantSummary.innerHTML = `<span class="participant-score">${participant.score} van ${state.availablePoints} punten</span> · ${participant.poolPositionScore} uit poulestanden${state.worstThirdsComplete ? ` · ${participant.worstThirdScore} uit slechtste nummers drie` : ""}`;

  elements.poolDetails.innerHTML = groupedColumns().map(([pool, columns]) => {
    const actual = state.resultsByPool.get(pool);
    const poolScore = participant.poolScores.get(pool);
    const pointsLabel = actual?.complete ? `${poolScore} / 4 punten` : "Nog niet gescoord";
    const pointsClass = actual?.complete ? "" : " pool-points--pending";

    const rows = columns.map((column) => {
      const predicted = Number(participant[column.kolom]);
      const actualPosition = actual?.positions.get(column.kolom);
      const isComplete = actual?.complete;
      const resultClass = !isComplete ? "pending" : predicted === actualPosition ? "position-correct" : "position-wrong";
      const actualText = actualPosition ?? "–";
      const marker = !isComplete ? "" : predicted === actualPosition ? " ✓" : "";
      return `
        <tr>
          <td>${escapeHtml(column.land)}</td>
          <td class="${resultClass}">${predicted}${marker}</td>
          <td class="${isComplete ? "" : "pending"}">${actualText}</td>
        </tr>`;
    }).join("");

    return `
      <article class="pool-card">
        <div class="pool-card__header">
          <h3>Poule ${pool}</h3>
          <span class="pool-points${pointsClass}">${pointsLabel}</span>
        </div>
        <table class="pool-table">
          <thead><tr><th>Land</th><th>Voorspeld</th><th>Echt</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </article>`;
  }).join("");

  renderWorstThirds(participant);
  renderBonus(participant);
}

function selectParticipant(name, scroll = true) {
  const participant = state.ranking.find((item) => item.naam === name);
  if (!participant) return;
  state.selectedName = name;
  renderParticipant(participant);
  elements.participantSection.hidden = false;
  history.replaceState(null, "", `#deelnemer=${encodeURIComponent(name)}`);
  if (scroll) elements.participantSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closeParticipant() {
  state.selectedName = null;
  elements.participantSection.hidden = true;
  history.replaceState(null, "", `${location.pathname}${location.search}`);
}

function showWarnings(warnings) {
  if (!warnings.length) {
    elements.warningPanel.hidden = true;
    return;
  }
  elements.warningPanel.innerHTML = `<strong>Let op bij de uitslagen:</strong><ul>${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>`;
  elements.warningPanel.hidden = false;
}

function showFatalError(error) {
  console.error(error);
  elements.errorPanel.innerHTML = `<strong>De stand kon niet worden geladen.</strong><br>${escapeHtml(error.message)}<br><br>Start de website via <code>start_website.bat</code> of een webserver.`;
  elements.errorPanel.hidden = false;
  elements.loadStatus.textContent = "Laden mislukt";
  elements.livePill.classList.add("is-error");
}

function openParticipantFromHash() {
  const match = location.hash.match(/^#deelnemer=(.+)$/);
  if (!match) return;
  try {
    selectParticipant(decodeURIComponent(match[1]), false);
  } catch {
    // Ongeldige hash negeren.
  }
}

async function initialize() {
  try {
    const [predictions, columns, results, worstThirds] = await Promise.all([
      loadCsv(DATA_FILES.predictions),
      loadCsv(DATA_FILES.columns),
      loadCsv(DATA_FILES.results),
      loadCsv(DATA_FILES.worstThirds),
    ]);

    if (!predictions.length) throw new Error("Er zijn nog geen deelnemers gevonden.");
    if (!columns.length) throw new Error("De poule-indeling ontbreekt.");

    state.predictions = predictions;
    state.columns = columns;
    const warnings = [
      ...prepareResults(results),
      ...prepareWorstThirds(worstThirds),
    ];
    buildRanking();
    renderSummary();
    renderRanking();
    showWarnings([...new Set(warnings)]);
    openParticipantFromHash();

    elements.loadStatus.textContent = "Stand is actueel";
    elements.livePill.classList.add("is-ready");
  } catch (error) {
    showFatalError(error instanceof Error ? error : new Error(String(error)));
  }
}

elements.searchInput.addEventListener("input", (event) => renderRanking(event.target.value));
elements.closeDetails.addEventListener("click", closeParticipant);
window.addEventListener("hashchange", openParticipantFromHash);

initialize();
