#!/usr/bin/env python3
"""Bereken de bonusstand vanuit twee CSV-bestanden.

Je vult ``bonus_uitslagen.csv`` stap voor stap aan. Lege velden blijven open en
worden nog niet nagekeken. Na iedere wijziging draai je opnieuw:

    python bereken_bonuspunten.py

Standaard worden deze bestanden gebruikt:
- bonus_voorspellingen_genormaliseerd.csv
- bonus_uitslagen_twee_topscorers.csv
- bonus_scores.csv

Trump telt niet mee en levert altijd 0 punten op.
Weghorst: 5 punten, met 1 punt aftrek per begonnen schijf van 5 minuten verschil.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

ONDERDELEN = (
    ("finalisten", 15),
    ("kampioen", 15),
    ("topscorer", 15),
    ("topscorer_doelpunten", 15),
    ("gele_kaarten", 15),
    ("land_meeste_kaarten", 10),
    ("weghorst_minuten", 5),
)

UITSLAG_KOLOMMEN = [
    "finalist_1",
    "finalist_2",
    "kampioen",
    "topscorer_1",
    "topscorer_2",
    "topscorer_doelpunten",
    "gele_kaarten",
    "land_meeste_kaarten",
    "weghorst_minuten",
]


def vergelijktekst(value: object) -> str:
    """Accent-, leesteken- en hoofdletterongevoelige vergelijking."""
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().strip()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def gelijk(a: object, b: object) -> bool:
    return bool(vergelijktekst(a)) and vergelijktekst(a) == vergelijktekst(b)


def ingevuld(value: object) -> bool:
    return str(value or "").strip() != ""


def lees_int(value: object, standaard: int | None = None) -> int | None:
    text = str(value or "").strip()
    if not text:
        return standaard
    try:
        return int(float(text.replace(",", ".")))
    except ValueError:
        return standaard


def lees_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as bestand:
        return list(csv.DictReader(bestand))


def maak_uitslagtemplate(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as bestand:
        writer = csv.DictWriter(bestand, fieldnames=UITSLAG_KOLOMMEN)
        writer.writeheader()
        writer.writerow({kolom: "" for kolom in UITSLAG_KOLOMMEN})


def lees_uitslagen(path: Path) -> dict[str, str]:
    if not path.exists():
        maak_uitslagtemplate(path)
        print(f"Uitslagtemplate aangemaakt: {path}")
        return {kolom: "" for kolom in UITSLAG_KOLOMMEN}

    rows = lees_csv(path)
    if not rows:
        return {kolom: "" for kolom in UITSLAG_KOLOMMEN}

    row = rows[0]
    return {kolom: str(row.get(kolom, "") or "").strip() for kolom in UITSLAG_KOLOMMEN}


def onderdeel_status(uitslagen: dict[str, str]) -> dict[str, bool]:
    return {
        "finalisten": ingevuld(uitslagen["finalist_1"]) and ingevuld(uitslagen["finalist_2"]),
        "kampioen": ingevuld(uitslagen["kampioen"]),
        "topscorer": ingevuld(uitslagen["topscorer_1"]) and ingevuld(uitslagen["topscorer_2"]),
        "topscorer_doelpunten": lees_int(uitslagen["topscorer_doelpunten"]) is not None,
        "gele_kaarten": lees_int(uitslagen["gele_kaarten"]) is not None,
        "land_meeste_kaarten": ingevuld(uitslagen["land_meeste_kaarten"]),
        "weghorst_minuten": lees_int(uitslagen["weghorst_minuten"]) is not None,
    }


def punten_of_leeg(openstaand: bool, punten: int) -> int | str:
    return punten if openstaand else ""


def bereken_rij(
    row: dict[str, str],
    uitslagen: dict[str, str],
    verwerkt: dict[str, bool],
) -> dict[str, Any]:
    # 1. Finalisten: 15 punten als beide landen kloppen, volgorde maakt niet uit.
    finalisten_score = ""
    if verwerkt["finalisten"]:
        voorspeld = {
            vergelijktekst(row.get("finalist_1")),
            vergelijktekst(row.get("finalist_2")),
        }
        werkelijk = {
            vergelijktekst(uitslagen["finalist_1"]),
            vergelijktekst(uitslagen["finalist_2"]),
        }
        finalisten_score = 15 if "" not in voorspeld and voorspeld == werkelijk else 0

    # 2. Wereldkampioen.
    kampioen_score = punten_of_leeg(
        verwerkt["kampioen"],
        15 if gelijk(row.get("kampioen"), uitslagen["kampioen"]) else 0,
    )

    # 3a. Topscorer.
    topscorer_score = punten_of_leeg(
        verwerkt["topscorer"],
        15 if (gelijk(row.get("topscorer"), uitslagen["topscorer_1"]) or gelijk(row.get("topscorer"), uitslagen["topscorer_2"])) else 0,
    )

    # 3b. Aantal doelpunten: 15 startpunten, 2 aftrek per doelpunt verschil.
    goals_score: int | str = ""
    if verwerkt["topscorer_doelpunten"]:
        voorspeld = lees_int(row.get("topscorer_doelpunten"))
        werkelijk = lees_int(uitslagen["topscorer_doelpunten"])
        goals_score = (
            max(0, 15 - 2 * abs(voorspeld - werkelijk))
            if voorspeld is not None and werkelijk is not None
            else 0
        )

    # 4. Gele kaarten: 1 aftrek per begonnen schijf van 5 kaarten verschil.
    kaarten_score: int | str = ""
    if verwerkt["gele_kaarten"]:
        voorspeld = lees_int(row.get("gele_kaarten"))
        werkelijk = lees_int(uitslagen["gele_kaarten"])
        kaarten_score = (
            max(0, 15 - math.ceil(abs(voorspeld - werkelijk) / 5))
            if voorspeld is not None and werkelijk is not None
            else 0
        )

    # Trump telt niet mee.
    trump_score = 0

    # 5. Land met de meeste kaarten.
    meeste_kaarten_score = punten_of_leeg(
        verwerkt["land_meeste_kaarten"],
        10
        if gelijk(row.get("land_meeste_kaarten"), uitslagen["land_meeste_kaarten"])
        else 0,
    )

    # 6. Weghorst: 5 punten, -1 per begonnen schijf van 5 minuten verschil.
    weghorst_score: int | str = ""
    if verwerkt["weghorst_minuten"]:
        voorspeld = lees_int(row.get("weghorst_minuten"))
        werkelijk = lees_int(uitslagen["weghorst_minuten"])
        weghorst_score = (
            max(0, 5 - math.ceil(abs(voorspeld - werkelijk) / 5))
            if voorspeld is not None and werkelijk is not None
            else 0
        )

    handmatig = lees_int(row.get("handmatige_correctie"), 0) or 0
    scorevelden = [
        finalisten_score,
        kampioen_score,
        topscorer_score,
        goals_score,
        kaarten_score,
        meeste_kaarten_score,
        weghorst_score,
    ]
    totaal = sum(value for value in scorevelden if isinstance(value, int)) + handmatig
    aantal_verwerkt = sum(verwerkt.values())
    beschikbaar = sum(maximum for naam, maximum in ONDERDELEN if verwerkt[naam])

    return {
        "naam": row.get("naam", ""),
        "punten_finalisten": finalisten_score,
        "punten_kampioen": kampioen_score,
        "punten_topscorer": topscorer_score,
        "punten_topscorer_doelpunten": goals_score,
        "punten_gele_kaarten": kaarten_score,
        "punten_trump": trump_score,
        "punten_land_meeste_kaarten": meeste_kaarten_score,
        "punten_weghorst": weghorst_score,
        "handmatige_correctie": handmatig,
        "totaal": totaal,
        "beschikbare_punten": beschikbaar,
        "onderdelen_verwerkt": aantal_verwerkt,
        "onderdelen_totaal": len(ONDERDELEN),
        "status": "compleet" if aantal_verwerkt == len(ONDERDELEN) else "voorlopig",
        "controle_opmerking": row.get("controle_opmerking", ""),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bereken een voorlopige of complete bonusstand vanuit CSV-bestanden."
    )
    parser.add_argument(
        "voorspellingen_csv",
        nargs="?",
        default="bonus_voorspellingen_genormaliseerd.csv",
        help="CSV met genormaliseerde voorspellingen.",
    )
    parser.add_argument(
        "-u",
        "--uitslagen",
        default="bonus_uitslagen_twee_topscorers.csv",
        help="CSV met de werkelijke bonusuitslagen; lege velden blijven open.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="bonus_scores.csv",
        help="Uitvoerbestand met de voorlopige bonusstand.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    voorspellingen_path = Path(args.voorspellingen_csv)
    uitslagen_path = Path(args.uitslagen)
    output_path = Path(args.output)

    if not voorspellingen_path.exists():
        print(
            f"Fout: voorspellingenbestand niet gevonden: {voorspellingen_path}",
            file=sys.stderr,
        )
        return 1

    uitslagen = lees_uitslagen(uitslagen_path)
    verwerkt = onderdeel_status(uitslagen)
    voorspellingen = lees_csv(voorspellingen_path)

    scores = [bereken_rij(row, uitslagen, verwerkt) for row in voorspellingen]
    scores.sort(key=lambda item: (-int(item["totaal"]), vergelijktekst(item["naam"])))

    beschikbare_punten = scores[0]["beschikbare_punten"] if scores else 0
    vorige_score: int | None = None
    vorige_rang = 0
    for positie, item in enumerate(scores, start=1):
        if not beschikbare_punten:
            item["rang"] = ""
            continue
        score = int(item["totaal"])
        if score != vorige_score:
            vorige_rang = positie
            vorige_score = score
        item["rang"] = vorige_rang

    kolommen = [
        "rang",
        "naam",
        "punten_finalisten",
        "punten_kampioen",
        "punten_topscorer",
        "punten_topscorer_doelpunten",
        "punten_gele_kaarten",
        "punten_trump",
        "punten_land_meeste_kaarten",
        "punten_weghorst",
        "handmatige_correctie",
        "totaal",
        "beschikbare_punten",
        "onderdelen_verwerkt",
        "onderdelen_totaal",
        "status",
        "controle_opmerking",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as bestand:
        writer = csv.DictWriter(bestand, fieldnames=kolommen)
        writer.writeheader()
        writer.writerows(scores)

    openstaand = [naam for naam, _ in ONDERDELEN if not verwerkt[naam]]
    beschikbaar = sum(maximum for naam, maximum in ONDERDELEN if verwerkt[naam])
    print(f"Klaar: {output_path}")
    print(f"Deelnemers: {len(scores)}")
    print(f"Onderdelen verwerkt: {sum(verwerkt.values())}/{len(ONDERDELEN)}")
    print(f"Beschikbare punten: {beschikbaar}/90")
    print("Nog open: " + (", ".join(openstaand) if openstaand else "niets"))
    if scores:
        print(f"Voorlopige leider: {scores[0]['naam']} met {scores[0]['totaal']} punten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
