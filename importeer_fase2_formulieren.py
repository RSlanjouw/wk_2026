#!/usr/bin/env python3
"""Lees alle fase-2 DOCX-formulieren en maak één CSV-bestand.

Verwachte structuur:

data/
└── fase2/
    ├── fase1_punten.csv
    ├── formulieren/
    │   ├── formulier_tigo.docx
    │   └── ...
    └── voorspellingen_fase2.csv   # wordt door dit script gemaakt

Gebruik vanuit de repository-root:

    pip install python-docx
    python importeer_fase2_formulieren.py
"""

from __future__ import annotations

import argparse
import csv
import difflib
import re
import sys
import unicodedata
from pathlib import Path

from docx import Document


AANTAL_WEDSTRIJDEN = 16
VELDEN = [
    "naam",
    "wedstrijd",
    "thuis",
    "voorspeld_thuis",
    "uit",
    "voorspeld_uit",
    "winnaar_na_penalties",
    "bronbestand",
]


def normaliseer(waarde: object) -> str:
    tekst = unicodedata.normalize("NFD", str(waarde or ""))
    tekst = "".join(teken for teken in tekst if unicodedata.category(teken) != "Mn")
    tekst = tekst.casefold()
    tekst = re.sub(r"[^a-z0-9]+", " ", tekst)
    return " ".join(tekst.split())


def lees_csv(pad: Path) -> list[dict[str, str]]:
    if not pad.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {pad}")

    with pad.open("r", encoding="utf-8-sig", newline="") as bestand:
        return list(csv.DictReader(bestand))


def lees_naam(document: Document) -> str:
    # Werkt voor een tabelrij zoals: Naam: | Ruben
    for tabel in document.tables:
        for rij in tabel.rows:
            cellen = [cel.text.strip() for cel in rij.cells]
            if len(cellen) >= 2 and normaliseer(cellen[0]).startswith("naam"):
                return cellen[1].strip()

    # Fallback voor een gewone tekstregel: Naam: Ruben
    for alinea in document.paragraphs:
        match = re.search(r"\bnaam\s*:\s*(.+)$", alinea.text, flags=re.I)
        if match:
            return match.group(1).strip()

    return ""


def parse_getal(
    waarde: str,
    *,
    veld: str,
    bron: Path,
    wedstrijd: int,
) -> int:
    tekst = waarde.strip()
    if not re.fullmatch(r"\d+", tekst):
        raise ValueError(
            f"{bron.name}: wedstrijd {wedstrijd} heeft geen geldig getal "
            f"bij {veld}: {waarde!r}"
        )
    return int(tekst)


def lees_wedstrijden(document: Document, bron: Path) -> list[dict[str, object]]:
    wedstrijden: list[dict[str, object]] = []

    for tabel in document.tables:
        for rij in tabel.rows:
            cellen = [cel.text.strip() for cel in rij.cells]

            if len(cellen) < 5 or not re.fullmatch(r"\d{1,2}", cellen[0]):
                continue

            nummer = int(cellen[0])
            if not 1 <= nummer <= AANTAL_WEDSTRIJDEN:
                continue

            thuis = cellen[1]
            voorspeld_thuis = parse_getal(
                cellen[2],
                veld="thuisdoelpunten",
                bron=bron,
                wedstrijd=nummer,
            )
            uit = cellen[3]
            voorspeld_uit = parse_getal(
                cellen[4],
                veld="uitdoelpunten",
                bron=bron,
                wedstrijd=nummer,
            )
            winnaar_penalties = cellen[5].strip() if len(cellen) >= 6 else ""

            if not thuis or not uit:
                raise ValueError(
                    f"{bron.name}: wedstrijd {nummer} mist een thuis- of uitteam."
                )

            if voorspeld_thuis != voorspeld_uit:
                winnaar_penalties = ""
            else:
                if not winnaar_penalties:
                    raise ValueError(
                        f"{bron.name}: wedstrijd {nummer} is gelijk voorspeld, "
                        "maar de winnaar na penalties ontbreekt."
                    )

                geldige_winnaars = {normaliseer(thuis), normaliseer(uit)}
                if normaliseer(winnaar_penalties) not in geldige_winnaars:
                    raise ValueError(
                        f"{bron.name}: penaltywinnaar {winnaar_penalties!r} "
                        f"hoort niet bij {thuis!r} tegen {uit!r}."
                    )

            wedstrijden.append(
                {
                    "wedstrijd": nummer,
                    "thuis": thuis,
                    "voorspeld_thuis": voorspeld_thuis,
                    "uit": uit,
                    "voorspeld_uit": voorspeld_uit,
                    "winnaar_na_penalties": winnaar_penalties,
                }
            )

    nummers = [int(item["wedstrijd"]) for item in wedstrijden]
    dubbel = sorted({nummer for nummer in nummers if nummers.count(nummer) > 1})
    if dubbel:
        raise ValueError(
            f"{bron.name}: dubbele wedstrijdnummers: "
            + ", ".join(map(str, dubbel))
        )

    wedstrijden.sort(key=lambda item: int(item["wedstrijd"]))

    gevonden = {int(item["wedstrijd"]) for item in wedstrijden}
    ontbrekend = [
        nummer
        for nummer in range(1, AANTAL_WEDSTRIJDEN + 1)
        if nummer not in gevonden
    ]
    if ontbrekend:
        raise ValueError(
            f"{bron.name}: ontbrekende wedstrijdnummers: "
            + ", ".join(map(str, ontbrekend))
        )

    return wedstrijden


def match_naam(
    formuliernaam: str,
    bekende_namen: dict[str, str],
    bron: Path,
) -> str:
    sleutel = normaliseer(formuliernaam)

    if sleutel in bekende_namen:
        return bekende_namen[sleutel]

    suggesties = difflib.get_close_matches(
        sleutel,
        list(bekende_namen),
        n=3,
        cutoff=0.65,
    )

    toevoeging = ""
    if suggesties:
        toevoeging = " Bedoelde je: " + ", ".join(
            bekende_namen[suggestie] for suggestie in suggesties
        ) + "?"

    raise ValueError(
        f"{bron.name}: naam {formuliernaam!r} komt niet voor "
        f"in fase1_punten.csv.{toevoeging}"
    )


def schrijf_csv(pad: Path, rijen: list[dict[str, object]]) -> None:
    pad.parent.mkdir(parents=True, exist_ok=True)

    with pad.open("w", encoding="utf-8-sig", newline="") as bestand:
        schrijver = csv.DictWriter(bestand, fieldnames=VELDEN)
        schrijver.writeheader()
        schrijver.writerows(rijen)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/fase2"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir: Path = args.data_dir
    formulieren_dir = data_dir / "formulieren"
    fase1_pad = data_dir / "fase1_punten.csv"
    uitvoer = args.output or data_dir / "voorspellingen_fase2.csv"

    try:
        fase1_rijen = lees_csv(fase1_pad)

        bekende_namen: dict[str, str] = {}
        for rij in fase1_rijen:
            naam = str(rij.get("naam", "")).strip()
            if not naam:
                continue

            sleutel = normaliseer(naam)
            if sleutel in bekende_namen and bekende_namen[sleutel] != naam:
                raise ValueError(
                    "fase1_punten.csv bevat twee namen die na normalisatie "
                    f"hetzelfde zijn: {bekende_namen[sleutel]!r} en {naam!r}."
                )
            bekende_namen[sleutel] = naam

        if not bekende_namen:
            raise ValueError("fase1_punten.csv bevat geen geldige namen.")

        if not formulieren_dir.exists():
            raise FileNotFoundError(
                f"Formulierenmap niet gevonden: {formulieren_dir}"
            )

        formulieren = sorted(formulieren_dir.glob("*.docx"))
        if not formulieren:
            raise ValueError(
                f"Geen DOCX-formulieren gevonden in {formulieren_dir}."
            )

        uitvoerrijen: list[dict[str, object]] = []
        al_ingelezen: dict[str, Path] = {}
        fouten: list[str] = []

        for bron in formulieren:
            try:
                document = Document(bron)
                formuliernaam = lees_naam(document)

                if not formuliernaam:
                    raise ValueError(f"{bron.name}: geen naam gevonden.")

                naam = match_naam(formuliernaam, bekende_namen, bron)
                naamsleutel = normaliseer(naam)

                if naamsleutel in al_ingelezen:
                    raise ValueError(
                        f"{bron.name}: voor {naam!r} is al een formulier "
                        f"ingelezen uit {al_ingelezen[naamsleutel].name!r}."
                    )

                wedstrijden = lees_wedstrijden(document, bron)

                for wedstrijd in wedstrijden:
                    uitvoerrijen.append(
                        {
                            "naam": naam,
                            **wedstrijd,
                            "bronbestand": bron.name,
                        }
                    )

                al_ingelezen[naamsleutel] = bron
                print(
                    f"OK: {bron.name} -> {naam} "
                    f"({len(wedstrijden)} wedstrijden)"
                )

            except Exception as fout:
                fouten.append(str(fout))
                print(f"FOUT: {fout}", file=sys.stderr)

        if fouten:
            print(
                "\nDe bestaande voorspellingen_fase2.csv is niet overschreven, "
                "omdat minstens één formulier ongeldig is.",
                file=sys.stderr,
            )
            return 1

        uitvoerrijen.sort(
            key=lambda rij: (
                normaliseer(rij["naam"]),
                int(rij["wedstrijd"]),
            )
        )
        schrijf_csv(uitvoer, uitvoerrijen)

        ontbrekende_namen = sorted(
            naam
            for sleutel, naam in bekende_namen.items()
            if sleutel not in al_ingelezen
        )

        print(f"\nGeschreven: {uitvoer.resolve()}")
        print(f"Formulieren geïmporteerd: {len(al_ingelezen)}")
        print(f"Voorspellingen geïmporteerd: {len(uitvoerrijen)}")

        if ontbrekende_namen:
            print("\nNog geen formulier voor:")
            for naam in ontbrekende_namen:
                print(f"- {naam}")

        return 0

    except Exception as fout:
        print(f"Fout: {fout}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
