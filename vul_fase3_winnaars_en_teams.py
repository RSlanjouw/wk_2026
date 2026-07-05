#!/usr/bin/env python3
"""Vul automatisch winnaars en vervolgteams in voor fase 3.

Dit script werkt op:

    data/fase3/voorspellingen_fase3.csv

Het doet per deelnemer:

1. Als `winnaar` leeg is en de voorspelde score niet gelijk is,
   wordt de winnaar automatisch uit de score bepaald.
2. Als een team in een kwartfinale, halve finale of finale leeg is,
   wordt dat team automatisch ingevuld met de winnaar van de vorige ronde.
3. Bij een voorspeld gelijkspel zonder ingevulde winnaar blijft de winnaar
   bewust leeg, omdat niet automatisch kan worden bepaald wie doorgaat.

Vaste bracketlogica:

    Kwartfinale 1 = winnaar B tegen winnaar A
    Kwartfinale 2 = winnaar E tegen winnaar F
    Kwartfinale 3 = winnaar C tegen winnaar D
    Kwartfinale 4 = winnaar G tegen winnaar H

    Halve finale X = winnaar kwartfinale 1 tegen winnaar kwartfinale 2
    Halve finale Y = winnaar kwartfinale 3 tegen winnaar kwartfinale 4

    Finale = winnaar halve finale X tegen winnaar halve finale Y

Gebruik vanuit de hoofdmap:

    python .\vul_fase3_winnaars_en_teams.py
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import defaultdict
from pathlib import Path


VELDEN = [
    "naam",
    "ronde",
    "wedstrijd",
    "thuis",
    "voorspeld_thuis",
    "uit",
    "voorspeld_uit",
    "winnaar",
    "bronbestand",
]


BRACKET = {
    ("qf", "1"): (("r16", "B"), ("r16", "A")),
    ("qf", "2"): (("r16", "E"), ("r16", "F")),
    ("qf", "3"): (("r16", "C"), ("r16", "D")),
    ("qf", "4"): (("r16", "G"), ("r16", "H")),
    ("sf", "X"): (("qf", "1"), ("qf", "2")),
    ("sf", "Y"): (("qf", "3"), ("qf", "4")),
    ("f", "F"): (("sf", "X"), ("sf", "Y")),
}


RONDE_VOLGORDE = {
    "r16": 0,
    "qf": 1,
    "sf": 2,
    "f": 3,
}


def lees_csv(pad: Path) -> list[dict[str, str]]:
    if not pad.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {pad}")

    with pad.open("r", encoding="utf-8-sig", newline="") as bestand:
        return list(csv.DictReader(bestand))


def schrijf_csv(
    pad: Path,
    rijen: list[dict[str, str]],
) -> None:
    with pad.open("w", encoding="utf-8-sig", newline="") as bestand:
        schrijver = csv.DictWriter(
            bestand,
            fieldnames=VELDEN,
            extrasaction="ignore",
        )
        schrijver.writeheader()
        schrijver.writerows(rijen)


def wedstrijdsleutel(rij: dict[str, str]) -> tuple[str, str]:
    ronde = str(rij.get("ronde", "")).strip()
    wedstrijd = str(rij.get("wedstrijd", "")).strip()

    if ronde == "f" and wedstrijd == "":
        wedstrijd = "F"
        rij["wedstrijd"] = "F"

    return ronde, wedstrijd


def bepaal_winnaar(rij: dict[str, str]) -> str:
    winnaar = str(rij.get("winnaar", "")).strip()

    if winnaar:
        return winnaar

    thuis = str(rij.get("thuis", "")).strip()
    uit = str(rij.get("uit", "")).strip()
    thuis_score = str(rij.get("voorspeld_thuis", "")).strip()
    uit_score = str(rij.get("voorspeld_uit", "")).strip()

    if (
        thuis == ""
        or uit == ""
        or thuis_score == ""
        or uit_score == ""
    ):
        return ""

    try:
        thuis_getal = int(thuis_score)
        uit_getal = int(uit_score)
    except ValueError:
        return ""

    if thuis_getal > uit_getal:
        return thuis

    if uit_getal > thuis_getal:
        return uit

    # Bij gelijkspel kan de penaltywinnaar niet worden geraden.
    return ""


def verwerk_deelnemer(
    naam: str,
    rijen: list[dict[str, str]],
) -> tuple[int, list[str]]:
    per_wedstrijd = {
        wedstrijdsleutel(rij): rij
        for rij in rijen
    }

    wijzigingen = 0
    meldingen: list[str] = []

    # Meerdere rondes na elkaar verwerken, zodat nieuwe winnaars meteen
    # gebruikt kunnen worden voor de volgende ronde.
    for ronde in ("r16", "qf", "sf", "f"):
        ronde_rijen = [
            rij
            for rij in rijen
            if wedstrijdsleutel(rij)[0] == ronde
        ]

        ronde_rijen.sort(
            key=lambda rij: str(
                wedstrijdsleutel(rij)[1]
            )
        )

        for rij in ronde_rijen:
            sleutel = wedstrijdsleutel(rij)

            # Vul vervolgteams vanuit de vorige ronde.
            if sleutel in BRACKET:
                bron_thuis, bron_uit = BRACKET[sleutel]

                vorige_thuis = per_wedstrijd.get(bron_thuis)
                vorige_uit = per_wedstrijd.get(bron_uit)

                afgeleid_thuis = (
                    bepaal_winnaar(vorige_thuis)
                    if vorige_thuis
                    else ""
                )
                afgeleid_uit = (
                    bepaal_winnaar(vorige_uit)
                    if vorige_uit
                    else ""
                )

                if (
                    str(rij.get("thuis", "")).strip() == ""
                    and afgeleid_thuis
                ):
                    rij["thuis"] = afgeleid_thuis
                    wijzigingen += 1

                if (
                    str(rij.get("uit", "")).strip() == ""
                    and afgeleid_uit
                ):
                    rij["uit"] = afgeleid_uit
                    wijzigingen += 1

                if (
                    str(rij.get("thuis", "")).strip() == ""
                    and not afgeleid_thuis
                ):
                    meldingen.append(
                        f"{naam}: {ronde} {sleutel[1]} thuisteam "
                        f"kon niet worden afgeleid uit {bron_thuis}."
                    )

                if (
                    str(rij.get("uit", "")).strip() == ""
                    and not afgeleid_uit
                ):
                    meldingen.append(
                        f"{naam}: {ronde} {sleutel[1]} uitteam "
                        f"kon niet worden afgeleid uit {bron_uit}."
                    )

            # Vul daarna de winnaar van deze wedstrijd vanuit de score.
            huidige_winnaar = str(
                rij.get("winnaar", "")
            ).strip()
            afgeleide_winnaar = bepaal_winnaar(rij)

            if not huidige_winnaar and afgeleide_winnaar:
                rij["winnaar"] = afgeleide_winnaar
                wijzigingen += 1

            if (
                not huidige_winnaar
                and not afgeleide_winnaar
                and str(rij.get("voorspeld_thuis", "")).strip() != ""
                and str(rij.get("voorspeld_uit", "")).strip() != ""
                and str(rij.get("voorspeld_thuis", "")).strip()
                == str(rij.get("voorspeld_uit", "")).strip()
            ):
                meldingen.append(
                    f"{naam}: {ronde} {sleutel[1]} is gelijk "
                    "voorspeld zonder winnaar; vervolgteam blijft leeg."
                )

    return wijzigingen, meldingen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "data/fase3/voorspellingen_fase3.csv"
        ),
    )
    parser.add_argument(
        "--geen-backup",
        action="store_true",
        help="Maak geen .bak-back-up van de bestaande CSV.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        rijen = lees_csv(args.input)

        per_deelnemer: dict[str, list[dict[str, str]]] = (
            defaultdict(list)
        )

        for rij in rijen:
            naam = str(rij.get("naam", "")).strip()

            if naam:
                per_deelnemer[naam].append(rij)

        totaal_wijzigingen = 0
        alle_meldingen: list[str] = []

        for naam, deelnemer_rijen in per_deelnemer.items():
            wijzigingen, meldingen = verwerk_deelnemer(
                naam,
                deelnemer_rijen,
            )
            totaal_wijzigingen += wijzigingen
            alle_meldingen.extend(meldingen)

        rijen.sort(
            key=lambda rij: (
                str(rij.get("naam", "")).casefold(),
                RONDE_VOLGORDE.get(
                    str(rij.get("ronde", "")).strip(),
                    99,
                ),
                str(rij.get("wedstrijd", "")),
            )
        )

        if not args.geen_backup:
            backup = args.input.with_suffix(
                args.input.suffix + ".bak"
            )
            shutil.copy2(args.input, backup)
            print(f"Back-up gemaakt: {backup}")

        schrijf_csv(args.input, rijen)

        print(f"Bijgewerkt: {args.input.resolve()}")
        print(f"Deelnemers: {len(per_deelnemer)}")
        print(f"Velden automatisch ingevuld: {totaal_wijzigingen}")

        if alle_meldingen:
            print("\nINFO:")
            for melding in sorted(set(alle_meldingen)):
                print(f"- {melding}")

        return 0

    except Exception as fout:
        print(f"FOUT: {fout}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
