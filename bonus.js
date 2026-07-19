"use strict";

const DATA = {
  scores: "bonus_scores.csv",
  predictions: "bonus_voorspellingen_genormaliseerd.csv",
  results: "bonus_uitslagen.csv",
};

const PARTS = [
  {
    key: "finalisten",
    label: "Finalisten",
    max: 15,
    score: "punten_finalisten",
    prediction: (row) => joinValues(row.finalist_1, row.finalist_2),
    actual: (row) => joinValues(row.finalist_1, row.finalist_2),
    ready: (row) => hasValue(row.finalist_1) && hasValue(row.finalist_2),
  },
  {
    key: "kampioen",
    label: "Wereldkampioen",
    max: 15,
    score: "punten_kampioen",
    prediction: (row) => display(row.kampioen),
    actual: (row) => display(row.kampioen),
    ready: (row) => hasValue(row.kampioen),
  },
  {
    key: "topscorer",
    label: "Topscorer",
    max: 15,
    score: "punten_topscorer",
    prediction: (row) => display(row.topscorer),
    actual: (row) => display(row.topscorer),
    ready: (row) => hasValue(row.topscorer),
  },
  {
    key: "topscorer_doelpunten",
    label: "Doelpunten topscorer",
    max: 15,
    score: "punten_topscorer_doelpunten",
    prediction: (row) => withUnit(row.topscorer_doelpunten, "goals"),
    actual: (row) => withUnit(row.topscorer_doelpunten, "goals"),
    ready: (row) => hasValue(row.topscorer_doelpunten),
  },
  {
    key: "gele_kaarten",
    label: "Gele kaarten",
    max: 15,
    score: "punten_gele_kaarten",
    prediction: (row) => withUnit(row.gele_kaarten, "kaarten"),
    actual: (row) => withUnit(row.gele_kaarten, "kaarten"),
    ready: (row) => hasValue(row.gele_kaarten),
  },
  {
    key: "land_meeste_kaarten",
    label: "Land met meeste kaarten",
    max: 10,
    score: "punten_land_meeste_kaarten",
    prediction: (row) => display(row.land_meeste_kaarten),
    actual: (row) => display(row.land_meeste_kaarten),
    ready: (row) => hasValue(row.land_meeste_kaarten),
  },
  {
    key: "weghorst_minuten",
    label: "Speelminuten Weghorst",
    max: 5,
    score: "punten_weghorst",
    prediction: (row) => withUnit(row.weghorst_minuten, "minuten"),
    actual: (row) => withUnit(row.weghorst_minuten, "minuten"),
    ready: (row) => hasValue(row.weghorst_minuten),
  },
];

const state = {
  scores: [],
  predictions: new Map(),
  results: {},
  lastModified: null,
};

const $ = (selector) => document.querySelector(selector);
const elements = {
  loadStatus: $("#load-status"),
  error: $("#error-panel"),
  participantCount: $("#participant-count"),
  completedParts: $("#completed-parts"),
  availablePoints: $("#available-points"),
  nextOpenPart: $("#next-open-part"),
  nextOpenDescription: $("#next-open-description"),
  lastUpdated: $("#last-updated"),
  rankingBody: $("#ranking-body"),
  searchInput: $("#search-input"),
  emptySearch: $("#empty-search"),
  participantSection: $("#participant-section"),
  participantTitle: $("#participant-title"),
  participantSummary: $("#participant-summary"),
  bonusDetails: $("#bonus-details"),
  closeDetails: $("#close-details"),
  detailTotal: $("#detail-total"),
  detailAvailable: $("#detail-available"),
  detailCompleted: $("#detail-completed"),
  detailStatus: $("#detail-status"),
};

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

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function hasValue(value) {
  return String(value ?? "").trim() !== "";
}

function display(value) {
  return hasValue(value) ? String(value).trim() : "–";
}

function joinValues(first, second) {
  if (!hasValue(first) && !hasValue(second)) return "–";
  return [display(first), display(second)].join(" – ");
}

function withUnit(value, unit) {
  return hasValue(value) ? `${String(value).trim()} ${unit}` : "–";
}

function parseCsv(text) {
  const source = text.replace(/^\uFEFF/, "");
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    const next = source[index + 1];

    if (quoted) {
      if (character === '"' && next === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      row.push(field);
      field = "";
    } else if (character === "\n") {
      row.push(field.replace(/\r$/, ""));
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }

  if (field !== "" || row.length) {
    row.push(field.replace(/\r$/, ""));
    if (row.some((value) => value !== "")) rows.push(row);
  }

  if (!rows.length) return [];
  const headers = rows[0].map((header) => header.trim());
  return rows.slice(1).map((values) =>
    Object.fromEntries(
      headers.map((header, index) => [header, (values[index] ?? "").trim()])
    )
  );
}

async function loadCsv(path) {
  const response = await fetch(`${path}?v=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} kon niet worden geladen (${response.status}).`);
  }
  return {
    rows: parseCsv(await response.text()),
    modified: response.headers.get("last-modified"),
  };
}

function buildState(scoreRows, predictionRows, resultRows, modifiedDates) {
  state.scores = scoreRows
    .filter((row) => hasValue(row.naam))
    .sort((a, b) => number(a.rang) - number(b.rang) || a.naam.localeCompare(b.naam, "nl"));

  state.predictions = new Map(
    predictionRows
      .filter((row) => hasValue(row.naam))
      .map((row) => [normalize(row.naam), row])
  );

  state.results = resultRows[0] ?? {};

  const validDates = modifiedDates
    .filter(Boolean)
    .map((value) => new Date(value))
    .filter((date) => !Number.isNaN(date.getTime()));
  state.lastModified = validDates.length
    ? new Date(Math.max(...validDates.map((date) => date.getTime())))
    : new Date();
}

function completedParts() {
  return PARTS.filter((part) => part.ready(state.results));
}

function renderSummary() {
  const completed = completedParts();
  const available = completed.reduce((total, part) => total + part.max, 0);
  const next = PARTS.find((part) => !part.ready(state.results));

  elements.participantCount.textContent = String(state.scores.length);
  elements.completedParts.textContent = String(completed.length);
  elements.availablePoints.textContent = String(available);

  if (next) {
    elements.nextOpenPart.textContent = next.label;
    elements.nextOpenDescription.textContent = "Vul dit veld later in bonus_uitslagen.csv in";
  } else {
    elements.nextOpenPart.textContent = "Alles verwerkt";
    elements.nextOpenDescription.textContent = "Het bonusklassement is compleet";
  }

  elements.lastUpdated.textContent = state.lastModified.toLocaleString("nl-NL", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function renderRanking(filter = "") {
  const query = normalize(filter);
  const rows = state.scores.filter((row) => normalize(row.naam).includes(query));
  elements.emptySearch.hidden = rows.length > 0;

  elements.rankingBody.innerHTML = rows
    .map((participant) => {
      const rank = hasValue(participant.rang) ? number(participant.rang) : null;
      const completed = number(participant.onderdelen_verwerkt);
      const totalParts = number(participant.onderdelen_totaal) || 7;
      const rankClass = rank && rank <= 3 ? ` rank-badge--${rank}` : "";
      return `
        <tr>
          <td>
            <span class="rank-badge${rankClass}">${rank ?? "–"}</span>
          </td>
          <td>
            <button class="name-button" type="button" data-name="${escapeHtml(participant.naam)}">
              ${escapeHtml(participant.naam)}
            </button>
          </td>
          <td><strong>${number(participant.totaal)}</strong></td>
          <td class="optional-column">${number(participant.beschikbare_punten)}</td>
          <td><span class="progress-pill">${completed}/${totalParts}</span></td>
          <td>
            <button class="detail-button" type="button" data-name="${escapeHtml(participant.naam)}" aria-label="Bekijk ${escapeHtml(participant.naam)}">›</button>
          </td>
        </tr>
      `;
    })
    .join("");

  elements.rankingBody.querySelectorAll("[data-name]").forEach((button) => {
    button.addEventListener("click", () => openParticipant(button.dataset.name));
  });
}

function scoreClass(scoreValue, ready) {
  if (!ready) return "points-open";
  return number(scoreValue) > 0 ? "points-positive" : "points-zero";
}

function renderBonusCards(participant, prediction) {
  elements.bonusDetails.innerHTML = PARTS.map((part) => {
    const ready = part.ready(state.results);
    const points = participant[part.score];
    const pointsText = ready ? `${number(points)} / ${part.max} punten` : "Nog open";

    return `
      <article class="bonus-card${ready ? "" : " is-open"}">
        <div class="bonus-card__header">
          <strong>${escapeHtml(part.label)}</strong>
          <span class="${scoreClass(points, ready)}">${escapeHtml(pointsText)}</span>
        </div>
        <div class="bonus-card__body">
          <div class="bonus-value">
            <span>Voorspelling</span>
            <strong>${escapeHtml(part.prediction(prediction))}</strong>
          </div>
          <div class="bonus-value">
            <span>Werkelijk</span>
            <strong>${escapeHtml(part.actual(state.results))}</strong>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

function openParticipant(name) {
  const participant = state.scores.find((row) => row.naam === name);
  const prediction = state.predictions.get(normalize(name));
  if (!participant || !prediction) return;

  elements.participantTitle.textContent = participant.naam;
  elements.participantSummary.textContent =
    `${number(participant.totaal)} van ${number(participant.beschikbare_punten)} beschikbare bonuspunten`;
  elements.detailTotal.textContent = String(number(participant.totaal));
  elements.detailAvailable.textContent = String(number(participant.beschikbare_punten));
  elements.detailCompleted.textContent =
    `${number(participant.onderdelen_verwerkt)} / ${number(participant.onderdelen_totaal) || 7}`;
  elements.detailStatus.textContent =
    participant.status === "compleet" ? "Compleet" : "Voorlopig";

  renderBonusCards(participant, prediction);
  elements.participantSection.hidden = false;
  elements.participantSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function initialize() {
  try {
    const [scores, predictions, results] = await Promise.all([
      loadCsv(DATA.scores),
      loadCsv(DATA.predictions),
      loadCsv(DATA.results),
    ]);

    buildState(
      scores.rows,
      predictions.rows,
      results.rows,
      [scores.modified, predictions.modified, results.modified]
    );
    renderSummary();
    renderRanking();
    elements.loadStatus.textContent = "Bonusstand is actueel";
  } catch (error) {
    console.error(error);
    elements.error.hidden = false;
    elements.error.innerHTML =
      `<strong>De bonusstand kon niet worden geladen.</strong><br>${escapeHtml(error.message)}`;
    elements.loadStatus.textContent = "Laden mislukt";
  }
}

elements.searchInput.addEventListener("input", (event) => renderRanking(event.target.value));
elements.closeDetails.addEventListener("click", () => {
  elements.participantSection.hidden = true;
});

initialize();
