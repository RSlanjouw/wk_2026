#!/usr/bin/env python3
"""Bereken de punten van fase 1 en schrijf data/fase1_punten.csv.

Gebruikte invoerbestanden:
- data/voorspellingen.csv
- data/kolommen.csv
- data/uitslagen.csv
- data/slechtste_nummers_drie.csv

Uitvoer:
- data/fase1_punten.csv

De puntentelling is gelijk aan die van app.js:
- 1 punt per correct voorspelde positie in een volledig ingevulde poule;
- 3 punten per correct voorspelde slechtste nummer drie;
- onvolledige poules en een onvolledige lijst slechtste nummers drie tellen nog niet mee.
"""

from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path


POOLS = tuple("ABCDEFGHIJKL")
PREFERRED_WORST_THIRD_FIELDS = tuple(
    f"slechtste_3_{index}" for index in range(1, 5)
)
LEGACY_WORST_THIRD_FIELDS = tuple(
    f"bonus_a{index}" for index in range(1, 5)
)


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(
        "".join(char.lower() if char.isalnum() else " " for char in text).split()
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "naam",
        "punten_fase1",
        "punten_poules",
        "punten_slechtste_nummers_drie",
        "voltreffers",
        "afgeronde_poules",
        "beschikbare_punten",
    ]

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_columns(rows: list[dict[str, str]]) -> tuple[
    dict[str, list[dict[str, str]]],
    dict[tuple[str, str], str],
    dict[str, str],
]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    column_by_pool_team: dict[tuple[str, str], str] = {}
    canonical_team_by_normalized: dict[str, str] = {}

    for row in rows:
        pool = str(row.get("poule", "")).strip().upper()
        column = str(row.get("kolom", "")).strip()
        team = str(row.get("land", "")).strip()

        if not pool or not column or not team:
            continue

        item = {"poule": pool, "kolom": column, "land": team}
        grouped[pool].append(item)
        column_by_pool_team[(pool, normalize(team))] = column
        canonical_team_by_normalized[normalize(team)] = team

    for pool in grouped:
        grouped[pool].sort(key=lambda item: item["kolom"])

    return grouped, column_by_pool_team, canonical_team_by_normalized


def prepare_results(
    result_rows: list[dict[str, str]],
    grouped_columns: dict[str, list[dict[str, str]]],
    column_by_pool_team: dict[tuple[str, str], str],
) -> tuple[dict[str, dict[str, int]], list[str]]:
    raw_positions: dict[str, dict[str, int]] = defaultdict(dict)
    warnings: list[str] = []

    for row in result_rows:
        pool = str(row.get("poule", "")).strip().upper()
        team = str(row.get("land", "")).strip()
        position_text = str(row.get("positie", "")).strip()

        if not pool and not team and not position_text:
            continue
        if not pool or not team:
            warnings.append("Een regel in uitslagen.csv mist een poule of land.")
            continue
        if not position_text:
            continue

        column = column_by_pool_team.get((pool, normalize(team)))
        if column is None:
            warnings.append(f"Onbekend land in poule {pool}: {team}.")
            continue

        try:
            position = int(position_text)
        except ValueError:
            warnings.append(f"{team} heeft een ongeldige positie: {position_text}.")
            continue

        if position not in {1, 2, 3, 4}:
            warnings.append(f"{team} heeft een ongeldige positie: {position_text}.")
            continue

        raw_positions[pool][column] = position

    completed: dict[str, dict[str, int]] = {}

    for pool in POOLS:
        columns = grouped_columns.get(pool, [])
        values = [
            raw_positions[pool].get(item["kolom"])
            for item in columns
            if item["kolom"] in raw_positions[pool]
        ]

        if len(columns) == 4 and len(values) == 4 and set(values) == {1, 2, 3, 4}:
            completed[pool] = raw_positions[pool]
        elif values:
            warnings.append(
                f"Poule {pool} is niet compleet of bevat dubbele posities en telt niet mee."
            )

    return completed, sorted(set(warnings))


def prepare_worst_thirds(
    rows: list[dict[str, str]],
    canonical_team_by_normalized: dict[str, str],
) -> tuple[set[str], bool, list[str]]:
    teams: set[str] = set()
    warnings: list[str] = []
    filled = 0

    for row in rows:
        team = str(row.get("land", "")).strip()
        if not team:
            continue

        filled += 1
        key = normalize(team)

        if key not in canonical_team_by_normalized:
            warnings.append(f"Onbekend land bij slechtste nummers drie: {team}.")
            continue
        if key in teams:
            warnings.append(f"{team} staat dubbel in slechtste_nummers_drie.csv.")
            continue

        teams.add(key)

    complete = len(teams) == 4

    if filled and not complete:
        warnings.append(
            "De vier slechtste nummers drie zijn niet compleet en tellen daarom niet mee."
        )
    if len(teams) > 4:
        warnings.append("Er mogen precies vier slechtste nummers drie worden ingevuld.")
        complete = False

    return teams, complete, sorted(set(warnings))


def predicted_worst_thirds(prediction: dict[str, str]) -> list[str]:
    preferred = [
        str(prediction.get(field, "")).strip()
        for field in PREFERRED_WORST_THIRD_FIELDS
    ]
    if any(preferred):
        return [team for team in preferred if team]

    return [
        str(prediction.get(field, "")).strip()
        for field in LEGACY_WORST_THIRD_FIELDS
        if str(prediction.get(field, "")).strip()
    ]


def score_participant(
    prediction: dict[str, str],
    grouped_columns: dict[str, list[dict[str, str]]],
    completed_results: dict[str, dict[str, int]],
    actual_worst_thirds: set[str],
    worst_thirds_complete: bool,
) -> dict[str, object]:
    pool_points = 0
    perfect_pools = 0

    for pool, actual_positions in completed_results.items():
        score = 0

        for column in grouped_columns[pool]:
            predicted_text = str(prediction.get(column["kolom"], "")).strip()
            try:
                predicted_position = int(predicted_text)
            except ValueError:
                continue

            if predicted_position == actual_positions[column["kolom"]]:
                score += 1

        pool_points += score
        if score == 4:
            perfect_pools += 1

    unique_predictions: set[str] = set()
    for team in predicted_worst_thirds(prediction):
        key = normalize(team)
        if key:
            unique_predictions.add(key)

    worst_third_hits = (
        len(unique_predictions & actual_worst_thirds)
        if worst_thirds_complete
        else 0
    )
    worst_third_points = worst_third_hits * 3
    total = pool_points + worst_third_points
    available = len(completed_results) * 4 + (12 if worst_thirds_complete else 0)

    return {
        "naam": str(prediction.get("naam", "")).strip(),
        "punten_fase1": total,
        "punten_poules": pool_points,
        "punten_slechtste_nummers_drie": worst_third_points,
        "voltreffers": perfect_pools,
        "afgeronde_poules": len(completed_results),
        "beschikbare_punten": available,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Standaard: <data-dir>/fase1_punten.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir
    output = args.output or data_dir / "fase1_punten.csv"

    try:
        predictions = read_csv(data_dir / "voorspellingen.csv")
        columns = read_csv(data_dir / "kolommen.csv")
        results = read_csv(data_dir / "uitslagen.csv")
        worst_thirds = read_csv(data_dir / "slechtste_nummers_drie.csv")

        (
            grouped_columns,
            column_by_pool_team,
            canonical_team_by_normalized,
        ) = load_columns(columns)

        if not grouped_columns:
            raise ValueError("kolommen.csv bevat geen geldige poule-indeling.")

        completed_results, result_warnings = prepare_results(
            results,
            grouped_columns,
            column_by_pool_team,
        )
        actual_worst_thirds, worst_thirds_complete, worst_warnings = (
            prepare_worst_thirds(
                worst_thirds,
                canonical_team_by_normalized,
            )
        )

        output_rows = [
            score_participant(
                prediction,
                grouped_columns,
                completed_results,
                actual_worst_thirds,
                worst_thirds_complete,
            )
            for prediction in predictions
            if str(prediction.get("naam", "")).strip()
        ]

        output_rows.sort(
            key=lambda row: (
                -int(row["punten_fase1"]),
                -int(row["punten_slechtste_nummers_drie"]),
                -int(row["voltreffers"]),
                str(row["naam"]).casefold(),
            )
        )

        write_csv(output, output_rows)

        print(f"Geschreven: {output.resolve()}")
        print(f"Deelnemers: {len(output_rows)}")
        print(f"Afgeronde poules: {len(completed_results)} / 12")
        print(
            "Slechtste nummers drie: "
            + ("compleet" if worst_thirds_complete else "nog niet compleet")
        )
        available = len(completed_results) * 4 + (
            12 if worst_thirds_complete else 0
        )
        print(f"Beschikbare punten fase 1: {available} / 60")

        warnings = result_warnings + worst_warnings
        if warnings:
            print("\nWaarschuwingen:")
            for warning in warnings:
                print(f"- {warning}")

        return 0

    except (FileNotFoundError, ValueError, csv.Error) as error:
        print(f"Fout: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
