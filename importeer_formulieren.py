#!/usr/bin/env python3
"""Lees alle WK-pouleformulieren uit een lokale map en maak één compacte CSV.

Standaard:
    invoer:  data/formulieren/
    uitvoer: data/voorspellingen.csv

Gebruik:
    python importeer_formulieren.py
    python importeer_formulieren.py --invoer "C:/mijn/formulieren"
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import unicodedata
from pathlib import Path

from docx import Document
from pypdf import PdfReader

# Verberg onschuldige herstelmeldingen van beschadigde PDF-verwijzingen.
logging.getLogger("pypdf").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "formulieren"
DEFAULT_OUTPUT = ROOT / "data" / "voorspellingen.csv"
DEFAULT_ERRORS = ROOT / "data" / "import_fouten.csv"
DEFAULT_MAPPING = ROOT / "data" / "kolommen.csv"
DEFAULT_WORST_THIRDS = ROOT / "data" / "slechtste_nummers_drie.csv"

POOLS: dict[str, list[str]] = {
    "A": ["Zuid-Afrika", "Zuid-Korea", "Mexico", "Tsjechië"],
    "B": ["Qatar", "Canada", "Zwitserland", "Bosnië en Herzegovina"],
    "C": ["Marokko", "Brazilië", "Schotland", "Haïti"],
    "D": ["Verenigde Staten", "Paraguay", "Australië", "Turkije"],
    "E": ["Ivoorkust", "Ecuador", "Duitsland", "Curaçao"],
    "F": ["Tunesië", "Japan", "Nederland", "Zweden"],
    "G": ["Egypte", "Nieuw-Zeeland", "Iran", "België"],
    "H": ["Uruguay", "Saoedi-Arabië", "Spanje", "Kaapverdië"],
    "I": ["Senegal", "Noorwegen", "Frankrijk", "Irak"],
    "J": ["Jordanië", "Algerije", "Oostenrijk", "Argentinië"],
    "K": ["Portugal", "Colombia", "DR Congo", "Oezbekistan"],
    "L": ["Ghana", "Kroatië", "Engeland", "Panama"],
}

COLUMNS = [f"{pool}{index}" for pool in POOLS for index in range(1, 5)]
TEAM_BY_COLUMN = {
    f"{pool}{index}": team
    for pool, teams in POOLS.items()
    for index, team in enumerate(teams, start=1)
}

WORST_THIRD_COLUMNS = [
    "slechtste_3_1",
    "slechtste_3_2",
    "slechtste_3_3",
    "slechtste_3_4",
]

BONUS_COLUMNS = [
    "bonus_finale",
    "bonus_topscorer",
    "bonus_kaarten",
    "bonus_trump",
    "bonus_kaartenland",
    "bonus_weghorst",
]

ANSWER_COLUMNS = [*WORST_THIRD_COLUMNS, *BONUS_COLUMNS]
EMPTY_ANSWERS = {column: "" for column in ANSWER_COLUMNS}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().replace("–", "-").replace("—", "-")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


ALIASES: dict[str, str] = {normalize(team): team for teams in POOLS.values() for team in teams}
ALIASES.update({
    "brazilie": "Brazilië",
    "belgie": "België",
    "tunesie": "Tunesië",
    "australie": "Australië",
    "curacao": "Curaçao",
    "kaapverdie": "Kaapverdië",
    "tsjechie": "Tsjechië",
    "haiti": "Haïti",
    "jordanie": "Jordanië",
    "kroatie": "Kroatië",
    "saoedi arabie": "Saoedi-Arabië",
    "saoudi arabie": "Saoedi-Arabië",
    "bosnie en herzegovina": "Bosnië en Herzegovina",
})


def canonical_team(value: str) -> str:
    key = normalize(value)
    if key in ALIASES:
        return ALIASES[key]
    candidates = [(len(alias), team) for alias, team in ALIASES.items() if alias and alias in key]
    return max(candidates)[1] if candidates else value.strip()


def validate_prediction(name: str, positions: dict[str, int]) -> None:
    missing = [team for team in TEAM_BY_COLUMN.values() if team not in positions]
    if missing:
        raise ValueError(f"{len(missing)} landen ontbreken: {', '.join(missing[:5])}")

    for pool, teams in POOLS.items():
        values = [positions[team] for team in teams]
        if sorted(values) != [1, 2, 3, 4]:
            raise ValueError(f"Poule {pool} bevat geen geldige unieke posities 1,2,3,4: {values}")

    if not name.strip():
        raise ValueError("naam ontbreekt")


def clean_answer(value: str) -> str:
    return " ".join((value or "").replace("\n", " ").split()).strip(" ;|")


def find_bonus_tables(document: Document) -> tuple[list[str], dict[str, str]]:
    """Zoek de vier slechtste nummers drie en de bonusvragen zonder vaste tabelnummers te veronderstellen."""
    worst_thirds: list[str] = []
    answers = dict(EMPTY_ANSWERS)

    for table in document.tables:
        rows = [[clean_answer(cell.text) for cell in row.cells] for row in table.rows]
        if not rows:
            continue

        # De vier slechtste nummers drie staan meestal als vier rijen met één land per rij.
        if len(rows) == 4 and all(len(row) >= 1 for row in rows):
            candidates = [canonical_team(row[0]) for row in rows if row and row[0]]
            if len(candidates) == 4 and all(team in TEAM_BY_COLUMN.values() for team in candidates):
                worst_thirds = candidates
                continue

        # Bonusvragen staan als een Vraag/Antwoord-tabel.
        header = " ".join(rows[0]).casefold()
        if "vraag" not in header or "antwoord" not in header:
            continue

        for row in rows[1:]:
            if len(row) < 2:
                continue
            question = normalize(row[0])
            answer = clean_answer(row[1])
            if not answer:
                continue
            if "finale" in question and "wereldkampioen" in question:
                answers["bonus_finale"] = answer
            elif "topscorer" in question:
                answers["bonus_topscorer"] = answer
            elif "hoeveel" in question and "kaarten" in question:
                answers["bonus_kaarten"] = answer
            elif "trump" in question and "aftrap" in question:
                answers["bonus_trump"] = answer
            elif "land" in question and "meeste kaarten" in question:
                answers["bonus_kaartenland"] = answer
            elif "weghorst" in question and "speelminuten" in question:
                answers["bonus_weghorst"] = answer

    for index, team in enumerate(worst_thirds[:4], start=1):
        answers[f"slechtste_3_{index}"] = team
    return worst_thirds, answers


def parse_docx(path: Path) -> tuple[str, dict[str, int], dict[str, str]]:
    document = Document(path)
    if len(document.tables) < 2:
        raise ValueError("onverwacht DOCX-formaat: te weinig tabellen")

    name = document.tables[0].cell(0, 1).text.strip()
    positions: dict[str, int] = {}

    for row in document.tables[1].rows:
        cells = [cell.text.replace("\n", " ").strip() for cell in row.cells]
        for team_col in (0, 2, 4):
            if team_col + 1 >= len(cells) or not cells[team_col]:
                continue
            team = canonical_team(cells[team_col])
            if team not in TEAM_BY_COLUMN.values():
                continue
            match = re.search(r"\b([1-4])\b", cells[team_col + 1])
            if match:
                positions[team] = int(match.group(1))

    _, bonus = find_bonus_tables(document)
    validate_prediction(name, positions)
    return name, positions, bonus


def extract_teams_in_order(text: str) -> list[str]:
    normalized = normalize(text)
    matches: list[tuple[int, int, str]] = []
    for alias, team in ALIASES.items():
        for match in re.finditer(rf"\b{re.escape(alias)}\b", normalized):
            matches.append((match.start(), -len(alias), team))
    matches.sort()

    ordered: list[str] = []
    used_ranges: list[tuple[int, int]] = []
    for start, negative_length, team in matches:
        end = start - negative_length
        if any(start < used_end and end > used_start for used_start, used_end in used_ranges):
            continue
        if team not in ordered:
            ordered.append(team)
            used_ranges.append((start, end))
    return ordered


PDF_QUESTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("bonus_finale", re.compile(r"Welk(?:e)?\s+landen\s+spelen\s+de\s+finale\s+en\s+wie\s+wordt\s+wereldkampioen\s*\?", re.I)),
    ("bonus_topscorer", re.compile(r"Wie\s+wordt\s+topscorer\s+en\s+met\s+hoeveel\s+doelpunten\s*\?", re.I)),
    ("bonus_kaarten", re.compile(r"Hoeveel\s+gele(?:\s*/\s*rode)?\s+kaarten\s+worden\s+er\s+uitgedeeld\s*\?", re.I)),
    ("bonus_trump", re.compile(r"Bij\s+welke\s+wedstrijd\s*\(\s*en\s*\)\s+doet\s+Trump\s+de\s+aftrap.*?\?", re.I)),
    ("bonus_kaartenland", re.compile(r"Welk\s+land\s+scoort\s+de\s+meeste\s+kaarten\s*\?", re.I)),
    ("bonus_weghorst", re.compile(r"Hoeveel\s+speelminuten\s+gaat\s+Wout\s+Weghorst\s+maken\s*\?", re.I)),
]


def parse_pdf_bonus(compact: str) -> dict[str, str]:
    answers = dict(EMPTY_ANSWERS)

    worst_match = re.search(
        r"Tevens\s+willen\s+we\s+graag\s+weten\s+welke\s+vier\s+slechtste\s+nummers\s+drie.*?verlaten\s*:\s*(.*?)\s+Bonusvragen\s*:",
        compact,
        flags=re.I,
    )
    if worst_match:
        for index, team in enumerate(extract_teams_in_order(worst_match.group(1))[:4], start=1):
            answers[f"slechtste_3_{index}"] = team

    bonus_match = re.search(r"Bonusvragen\s*:\s*(.*?)(?:Voorbeeld\s+van\s+een\s+poule\s+voorspelling|$)", compact, flags=re.I)
    if not bonus_match:
        return answers

    bonus_text = re.sub(r"^Vraag\s+Antwoord\s*", "", bonus_match.group(1).strip(), flags=re.I)
    found: list[tuple[int, int, str]] = []
    for key, pattern in PDF_QUESTION_PATTERNS:
        match = pattern.search(bonus_text)
        if match:
            found.append((match.start(), match.end(), key))
    found.sort()

    for index, (_, end, key) in enumerate(found):
        next_start = found[index + 1][0] if index + 1 < len(found) else len(bonus_text)
        answers[key] = clean_answer(bonus_text[end:next_start])

    return answers


def parse_pdf(path: Path) -> tuple[str, dict[str, int], dict[str, str]]:
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    compact = " ".join(text.split())

    name_match = re.search(r"Naam:\s*(.*?)\s+Voor de poulefase", compact, flags=re.I)
    if not name_match:
        raise ValueError("naam niet gevonden")
    name = name_match.group(1).strip()

    start = re.search(r"Voor de poulefase.*?poule in:\s*", compact, flags=re.I)
    end = re.search(r"Tevens willen", compact, flags=re.I)
    if not start:
        raise ValueError("begin van poule-overzicht niet gevonden")
    pool_text = compact[start.end() : end.start() if end else len(compact)]
    normalized = normalize(pool_text)

    positions: dict[str, int] = {}
    for team in TEAM_BY_COLUMN.values():
        aliases = sorted(
            {alias for alias, canonical in ALIASES.items() if canonical == team},
            key=len,
            reverse=True,
        )
        for alias in aliases:
            match = re.search(rf"\b{re.escape(alias)}\b\s+([1-4])\b", normalized)
            if match:
                positions[team] = int(match.group(1))
                break

    bonus = parse_pdf_bonus(compact)
    validate_prediction(name, positions)
    return name, positions, bonus


def discover_files(folder: Path) -> list[Path]:
    supported = {".docx", ".pdf"}
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.casefold() in supported
        and not path.name.startswith("~$")
    )



def ensure_worst_thirds_template(path: Path) -> None:
    """Maak alleen een leeg invoerbestand als het nog niet bestaat."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["nummer", "land"])
        for number in range(1, 5):
            writer.writerow([number, ""])

def write_mapping(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kolom", "poule", "land"])
        for column in COLUMNS:
            writer.writerow([column, column[0], TEAM_BY_COLUMN[column]])


def write_predictions(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["naam", *COLUMNS, *ANSWER_COLUMNS])
        writer.writeheader()
        writer.writerows(rows)


def write_errors(path: Path, errors: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["bestand", "fout"])
        writer.writerows(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invoer", type=Path, default=DEFAULT_INPUT, help="map met DOCX- en PDF-formulieren")
    parser.add_argument("--uitvoer", type=Path, default=DEFAULT_OUTPUT, help="doelbestand voor de compacte CSV")
    args = parser.parse_args(argv)

    args.invoer.mkdir(parents=True, exist_ok=True)
    files = discover_files(args.invoer)
    if not files:
        print(f"Geen DOCX- of PDF-formulieren gevonden in: {args.invoer}")
        print("Plaats de formulieren in die map en voer het script opnieuw uit.")
        write_mapping(DEFAULT_MAPPING)
        ensure_worst_thirds_template(DEFAULT_WORST_THIRDS)
        return 1

    rows: list[dict[str, str | int]] = []
    errors: list[tuple[str, str]] = []
    names_seen: set[str] = set()

    for path in files:
        try:
            if path.suffix.casefold() == ".docx":
                name, positions, bonus = parse_docx(path)
            else:
                name, positions, bonus = parse_pdf(path)

            name_key = normalize(name)
            if name_key in names_seen:
                raise ValueError(f"dubbele deelnemer: {name}")
            names_seen.add(name_key)

            row: dict[str, str | int] = {"naam": name}
            for column in COLUMNS:
                row[column] = positions[TEAM_BY_COLUMN[column]]
            row.update(bonus)
            rows.append(row)
            print(f"OK  {path.name} -> {name}")
        except Exception as exc:  # één slecht bestand mag de rest niet blokkeren
            errors.append((path.name, str(exc)))
            print(f"FOUT {path.name}: {exc}", file=sys.stderr)

    rows.sort(key=lambda row: normalize(str(row["naam"])))
    write_predictions(args.uitvoer, rows)
    write_mapping(DEFAULT_MAPPING)
    ensure_worst_thirds_template(DEFAULT_WORST_THIRDS)
    write_errors(DEFAULT_ERRORS, errors)

    print()
    print(f"Klaar: {len(rows)} deelnemers geschreven naar {args.uitvoer}")
    if errors:
        print(f"Controleer {DEFAULT_ERRORS.name}: {len(errors)} bestand(en) konden niet worden verwerkt.")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
