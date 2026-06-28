"use strict";

const DATA = {
  phase1: "data/fase2/fase1_punten.csv",
  predictions: "data/fase2/voorspellingen_fase2.csv",
  results: "data/fase2/uitslagen_fase2.csv",
};

const state = {
  participants: [],
  predictions: [],
  results: new Map(),
  resultRows: [],
  completedMatches: 0,
  nextOpenMatch: null,
};

const $ = (selector) => document.querySelector(selector);

const elements = {
  loadStatus: $("#load-status"),
  error: $("#error-panel"),
  participantCount: $("#participant-count"),
  completedMatches: $("#completed-matches"),
  availablePoints: $("#available-points"),
  nextOpenMatch: $("#next-open-match"),
  nextOpenMatchNumber: $("#next-open-match-number"),
  lastUpdated: $("#last-updated"),
  rankingBody: $("#ranking-body"),
  searchInput: $("#search-input"),
  emptySearch: $("#empty-search"),
  participantSection: $("#participant-section"),
  participantTitle: $("#participant-title"),
  participantSummary: $("#participant-summary"),
  matchDetails: $("#match-details"),
  closeDetails: $("#close-details"),
  detailPhase1: $("#detail-phase1"),
  detailPhase2: $("#detail-phase2"),
  detailExact: $("#detail-exact"),
  detailTotal: $("#detail-total"),
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

      if (row.some((value) => value !== "")) {
        rows.push(row);
      }

      row = [];
      field = "";
    } else {
      field += character;
    }
  }

  if (field !== "" || row.length) {
    row.push(field.replace(/\r$/, ""));

    if (row.some((value) => value !== "")) {
      rows.push(row);
    }
  }

  if (!rows.length) {
    return [];
  }

  const headers = rows[0].map((header) => header.trim());

  return rows.slice(1).map((values) =>
    Object.fromEntries(
      headers.map((header, index) => [
        header,
        (values[index] ?? "").trim(),
      ])
    )
  );
}

async function loadCsv(path) {
  const response = await fetch(`${path}?v=${Date.now()}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `${path} kon niet worden geladen (${response.status}).`
    );
  }

  return parseCsv(await response.text());
}

function resultType(
  homeScore,
  awayScore,
  penaltyWinner,
  homeTeam,
  awayTeam
) {
  if (homeScore > awayScore) {
    return "home";
  }

  if (awayScore > homeScore) {
    return "away";
  }

  const winner = normalize(penaltyWinner);

  if (winner && winner === normalize(homeTeam)) {
    return "home";
  }

  if (winner && winner === normalize(awayTeam)) {
    return "away";
  }

  return "draw";
}

function scorePrediction(prediction, result) {
  if (!result) {
    return {
      points: 0,
      exact: false,
      processed: false,
    };
  }

  const predictedHome = number(prediction.voorspeld_thuis);
  const predictedAway = number(prediction.voorspeld_uit);
  const actualHome = number(result.werkelijk_thuis);
  const actualAway = number(result.werkelijk_uit);

  const predictedType = resultType(
    predictedHome,
    predictedAway,
    prediction.winnaar_na_penalties,
    prediction.thuis,
    prediction.uit
  );

  const actualType = resultType(
    actualHome,
    actualAway,
    result.winnaar_na_penalties,
    result.thuis,
    result.uit
  );

  const correctResult = predictedType === actualType;
  const correctScore =
    predictedHome === actualHome &&
    predictedAway === actualAway;

  const tieRequiresWinner = actualHome === actualAway;

  const correctPenaltyWinner =
    !tieRequiresWinner ||
    normalize(prediction.winnaar_na_penalties) ===
      normalize(result.winnaar_na_penalties);

  const exact = correctScore && correctPenaltyWinner;

  return {
    points: exact ? 5 : correctResult ? 3 : 0,
    exact,
    processed: true,
  };
}

function buildState(phase1Rows, predictionRows, resultRows) {
  state.predictions = predictionRows;
  state.resultRows = [...resultRows].sort(
    (a, b) => number(a.wedstrijd) - number(b.wedstrijd)
  );

  state.results = new Map(
    resultRows
      .filter(
        (row) =>
          String(row.werkelijk_thuis ?? "").trim() !== "" &&
          String(row.werkelijk_uit ?? "").trim() !== ""
      )
      .map((row) => [String(number(row.wedstrijd)), row])
  );

  state.completedMatches = state.results.size;

  state.nextOpenMatch =
    state.resultRows.find(
      (row) =>
        String(row.werkelijk_thuis ?? "").trim() === "" ||
        String(row.werkelijk_uit ?? "").trim() === ""
    ) ?? null;

  const predictionsByName = new Map();

  for (const prediction of predictionRows) {
    const key = normalize(prediction.naam);

    if (!predictionsByName.has(key)) {
      predictionsByName.set(key, []);
    }

    predictionsByName.get(key).push(prediction);
  }

  state.participants = phase1Rows
    .filter((row) => String(row.naam ?? "").trim())
    .map((row) => {
      const name = row.naam.trim();
      const predictions = predictionsByName.get(normalize(name)) ?? [];

      let phase2 = 0;
      let exact = 0;

      for (const prediction of predictions) {
        const result = state.results.get(
          String(number(prediction.wedstrijd))
        );

        const score = scorePrediction(prediction, result);

        phase2 += score.points;

        if (score.exact) {
          exact += 1;
        }
      }

      const phase1 = number(row.punten_fase1);

      return {
        name,
        phase1,
        phase2,
        exact,
        total: phase1 + phase2,
        hasForm: predictions.length > 0,
      };
    })
    .sort(
      (a, b) =>
        b.total - a.total ||
        b.phase2 - a.phase2 ||
        b.exact - a.exact ||
        a.name.localeCompare(b.name, "nl")
    );
}

function rankFor(index) {
  if (index === 0) {
    return 1;
  }

  const current = state.participants[index];
  const previous = state.participants[index - 1];

  if (
    current.total === previous.total &&
    current.phase2 === previous.phase2 &&
    current.exact === previous.exact
  ) {
    return rankFor(index - 1);
  }

  return index + 1;
}

function renderSummary() {
  elements.participantCount.textContent = String(
    state.participants.length
  );

  elements.completedMatches.textContent = String(
    state.completedMatches
  );

  elements.availablePoints.textContent = String(
    state.completedMatches * 5
  );

  if (state.nextOpenMatch) {
    elements.nextOpenMatch.textContent =
      `${state.nextOpenMatch.thuis} – ${state.nextOpenMatch.uit}`;
    elements.nextOpenMatchNumber.textContent =
      `Wedstrijd ${number(state.nextOpenMatch.wedstrijd)}`;
  } else {
    elements.nextOpenMatch.textContent = "Alles verwerkt";
    elements.nextOpenMatchNumber.textContent =
      "Alle 16 wedstrijden hebben een uitslag";
  }

  elements.lastUpdated.textContent = new Date().toLocaleString(
    "nl-NL",
    {
      dateStyle: "medium",
      timeStyle: "short",
    }
  );
}

function predictionForNextMatch(participantName) {
  if (!state.nextOpenMatch) {
    return null;
  }

  const matchNumber = number(state.nextOpenMatch.wedstrijd);

  return (
    state.predictions.find(
      (row) =>
        normalize(row.naam) === normalize(participantName) &&
        number(row.wedstrijd) === matchNumber
    ) ?? null
  );
}

function renderNextMatchPrediction(participantName) {
  const prediction = predictionForNextMatch(participantName);

  if (!state.nextOpenMatch) {
    return '<span class="next-prediction next-prediction--done">Alles verwerkt</span>';
  }

  if (!prediction) {
    return '<span class="next-prediction next-prediction--missing">Geen formulier</span>';
  }

  const penaltyWinner = prediction.winnaar_na_penalties
    ? `<small>p: ${escapeHtml(prediction.winnaar_na_penalties)}</small>`
    : "";

  return `
    <span class="next-prediction">
      <strong>
        ${number(prediction.voorspeld_thuis)}–${number(prediction.voorspeld_uit)}
      </strong>
      ${penaltyWinner}
    </span>
  `;
}

function renderRanking(filter = "") {
  const query = normalize(filter);

  const rows = state.participants
    .map((participant, index) => ({
      participant,
      rank: rankFor(index),
    }))
    .filter(({ participant }) =>
      normalize(participant.name).includes(query)
    );

  elements.emptySearch.hidden = rows.length > 0;

  elements.rankingBody.innerHTML = rows
    .map(
      ({ participant, rank }) => `
        <tr>
          <td>
            <span class="rank-badge${
              rank <= 3 ? ` rank-badge--${rank}` : ""
            }">
              ${rank}
            </span>
          </td>
          <td>
            <button
              class="name-button"
              type="button"
              data-name="${escapeHtml(participant.name)}"
            >
              ${escapeHtml(participant.name)}
            </button>
          </td>
          <td>${participant.phase1}</td>
          <td>${participant.phase2}</td>
          <td class="next-match-column">
            ${renderNextMatchPrediction(participant.name)}
          </td>
          <td class="optional-column">${participant.exact}</td>
          <td><strong>${participant.total}</strong></td>
          <td>
            <button
              class="detail-button"
              type="button"
              data-name="${escapeHtml(participant.name)}"
              aria-label="Bekijk ${escapeHtml(participant.name)}"
            >
              ›
            </button>
          </td>
        </tr>
      `
    )
    .join("");

  elements.rankingBody
    .querySelectorAll("[data-name]")
    .forEach((button) => {
      button.addEventListener("click", () => {
        openParticipant(button.dataset.name);
      });
    });
}

function renderMatches(name) {
  const rows = state.predictions
    .filter((row) => normalize(row.naam) === normalize(name))
    .sort((a, b) => {
      const nextNumber = state.nextOpenMatch
        ? number(state.nextOpenMatch.wedstrijd)
        : -1;

      const aIsNext = number(a.wedstrijd) === nextNumber;
      const bIsNext = number(b.wedstrijd) === nextNumber;

      if (aIsNext && !bIsNext) {
        return -1;
      }

      if (!aIsNext && bIsNext) {
        return 1;
      }

      return number(a.wedstrijd) - number(b.wedstrijd);
    });

  if (!rows.length) {
    elements.matchDetails.innerHTML =
      '<p class="empty-state">Nog geen formulier voor deze deelnemer.</p>';
    return;
  }

  elements.matchDetails.innerHTML = rows
    .map((prediction) => {
      const result = state.results.get(
        String(number(prediction.wedstrijd))
      );

      const score = scorePrediction(prediction, result);

      const actualHome = result
        ? result.werkelijk_thuis
        : "–";

      const actualAway = result
        ? result.werkelijk_uit
        : "–";

      const predictedPenalty =
        prediction.winnaar_na_penalties
          ? `Voorspelde penaltywinnaar: ${escapeHtml(
              prediction.winnaar_na_penalties
            )}`
          : "";

      const actualPenalty = result?.winnaar_na_penalties
        ? `Werkelijke penaltywinnaar: ${escapeHtml(
            result.winnaar_na_penalties
          )}`
        : "";

      const footer = [predictedPenalty, actualPenalty]
        .filter(Boolean)
        .join(" · ");

      const isNextOpen =
        state.nextOpenMatch &&
        number(prediction.wedstrijd) ===
          number(state.nextOpenMatch.wedstrijd);

      return `
        <article class="match-card${
          score.processed ? "" : " is-open"
        }${isNextOpen ? " is-next-open" : ""}">
          <div class="match-card__header">
            <strong>
              Wedstrijd ${number(prediction.wedstrijd)}
              ${isNextOpen ? '<span class="next-label">Eerstvolgende</span>' : ""}
            </strong>
            <span class="points-${score.points}">
              ${
                score.processed
                  ? `${score.points} punten`
                  : "Nog open"
              }
            </span>
          </div>

          <div class="match-card__teams">
            <div class="match-card__team">
              <span>${escapeHtml(prediction.thuis)}</span>
              <span class="match-card__score">
                ${number(prediction.voorspeld_thuis)}
              </span>
              <span class="match-card__actual">
                ${escapeHtml(actualHome)}
              </span>
            </div>

            <div class="match-card__team">
              <span>${escapeHtml(prediction.uit)}</span>
              <span class="match-card__score">
                ${number(prediction.voorspeld_uit)}
              </span>
              <span class="match-card__actual">
                ${escapeHtml(actualAway)}
              </span>
            </div>
          </div>

          ${
            footer
              ? `<div class="match-card__footer">${footer}</div>`
              : ""
          }
        </article>
      `;
    })
    .join("");
}

function openParticipant(name) {
  const participant = state.participants.find(
    (item) => item.name === name
  );

  if (!participant) {
    return;
  }

  elements.participantTitle.textContent = participant.name;

  elements.participantSummary.textContent =
    `${participant.phase1} punten in fase 1 · ` +
    `${participant.phase2} punten in fase 2`;

  elements.detailPhase1.textContent =
    `${participant.phase1} / 60`;

  elements.detailPhase2.textContent =
    `${participant.phase2} / ${state.completedMatches * 5}`;

  elements.detailExact.textContent =
    String(participant.exact);

  elements.detailTotal.textContent =
    String(participant.total);

  renderMatches(name);

  elements.participantSection.hidden = false;

  elements.participantSection.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

async function initialize() {
  try {
    const [phase1Rows, predictionRows, resultRows] =
      await Promise.all([
        loadCsv(DATA.phase1),
        loadCsv(DATA.predictions),
        loadCsv(DATA.results),
      ]);

    buildState(
      phase1Rows,
      predictionRows,
      resultRows
    );

    renderSummary();
    renderRanking();

    elements.loadStatus.textContent =
      "Stand is actueel";
  } catch (error) {
    console.error(error);

    elements.error.hidden = false;
    elements.error.innerHTML =
      `<strong>De stand kon niet worden geladen.</strong><br>` +
      escapeHtml(error.message);

    elements.loadStatus.textContent =
      "Laden mislukt";
  }
}

elements.searchInput.addEventListener(
  "input",
  (event) => {
    renderRanking(event.target.value);
  }
);

elements.closeDetails.addEventListener(
  "click",
  () => {
    elements.participantSection.hidden = true;
  }
);

initialize();
