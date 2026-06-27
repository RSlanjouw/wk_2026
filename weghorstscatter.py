#!/usr/bin/env python3
"""
Maak een echte scatterplot van de voorspelde speelminuten van Wout Weghorst.

Verwacht:
    data/voorspellingen.csv

Het script zoekt automatisch naar een kolom waarin 'weghorst' voorkomt.
Ook vrije tekst zoals '30min', '28 min' en
'ik denk 378 minuten' wordt herkend.

Uitvoer:
    weghorst_scatter.png
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
CSV_PAD = ROOT / "data" / "voorspellingen.csv"
UITVOER_PAD = ROOT / "weghorst_scatter.png"
NUMERIEKE_UITVOER_PAD = ROOT / "weghorst_numerieke_verdeling.png"
ORANJE = "#f58220"


def vind_weghorst_kolom(kolommen: list[str]) -> str:
    kandidaten = [kolom for kolom in kolommen if "weghorst" in kolom.lower()]

    if not kandidaten:
        raise ValueError(
            "Geen Weghorst-kolom gevonden in voorspellingen.csv.\n"
            f"Gevonden kolommen: {', '.join(kolommen)}"
        )

    return kandidaten[0]


def haal_minuten_uit_tekst(waarde: str) -> int | None:
    """
    Haal het eerste getal uit vrije tekst.

    Voorbeelden:
        30min -> 30
        28 min -> 28
        Ik denk 378 minuten -> 378
    """
    match = re.search(r"-?\d+(?:[.,]\d+)?", waarde)

    if not match:
        return None

    getal = match.group(0).replace(",", ".")
    return round(float(getal))


def lees_voorspellingen(
    csv_pad: Path,
) -> tuple[str, list[tuple[str, int]]]:
    if not csv_pad.exists():
        raise FileNotFoundError(f"CSV niet gevonden: {csv_pad}")

    with csv_pad.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as bestand:
        reader = csv.DictReader(bestand)

        if not reader.fieldnames:
            raise ValueError("De CSV heeft geen kolomkoppen.")

        weghorst_kolom = vind_weghorst_kolom(reader.fieldnames)
        waarden: list[tuple[str, int]] = []

        for regelnummer, rij in enumerate(reader, start=2):
            naam = (
                rij.get("naam")
                or rij.get("Naam")
                or ""
            ).strip()

            ruwe_waarde = (
                rij.get(weghorst_kolom)
                or ""
            ).strip()

            if not ruwe_waarde:
                continue

            minuten = haal_minuten_uit_tekst(ruwe_waarde)

            if minuten is None:
                print(
                    f"Waarschuwing: regel {regelnummer} overgeslagen; "
                    f"geen getal gevonden in '{ruwe_waarde}'.",
                    file=sys.stderr,
                )
                continue

            waarden.append(
                (
                    naam or f"Regel {regelnummer}",
                    minuten,
                )
            )

    return weghorst_kolom, waarden


def maak_scatterplot(
    waarden: list[tuple[str, int]],
    uitvoer_pad: Path,
) -> None:
    if not waarden:
        raise ValueError(
            "Geen geldige Weghorst-voorspellingen gevonden."
        )

    waarden = sorted(
        waarden,
        key=lambda item: (
            item[1],
            item[0].lower(),
        ),
    )

    namen = [naam for naam, _ in waarden]
    minuten = [waarde for _, waarde in waarden]
    x_posities = list(range(1, len(waarden) + 1))

    breedte = max(11, len(waarden) * 0.42)

    fig, ax = plt.subplots(
        figsize=(breedte, 7)
    )

    ax.scatter(
        x_posities,
        minuten,
        s=90,
        color=ORANJE,
        edgecolors="black",
        linewidths=0.7,
        zorder=3,
    )

    gemiddelde = sum(minuten) / len(minuten)

    ax.axhline(
        gemiddelde,
        color=ORANJE,
        linestyle="--",
        linewidth=1.5,
        alpha=0.75,
        label=f"Gemiddelde: {gemiddelde:.1f} minuten",
    )

    ax.set_title(
        "Hoeveel minuten krijgt Wout Weghorst?\n"
        "De één ziet een pinchhitter, "
        "de ander een volledige Netflix-serie.",
        fontsize=15,
        pad=14,
    )

    ax.set_xlabel("Deelnemers")
    ax.set_ylabel("Voorspelde speelminuten")

    ax.set_xticks(x_posities)
    ax.set_xticklabels(
        namen,
        rotation=55,
        ha="right",
    )

    ax.grid(
        axis="y",
        alpha=0.25,
        zorder=0,
    )

    ax.legend()

    verschil = max(minuten) - min(minuten)
    marge = max(
        10,
        round(verschil * 0.08),
    )

    ax.set_ylim(
        max(0, min(minuten) - marge),
        max(minuten) + marge,
    )

    for x, y in zip(x_posities, minuten):
        ax.annotate(
            str(y),
            (x, y),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=9,
        )

    fig.tight_layout()

    fig.savefig(
        uitvoer_pad,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)

def maak_numerieke_verdeling(
    waarden: list[tuple[str, int]],
    uitvoer_pad: Path,
) -> None:
    if not waarden:
        raise ValueError(
            "Geen geldige Weghorst-voorspellingen gevonden."
        )

    minuten = [waarde for _, waarde in waarden]

    minimum = min(minuten)
    maximum = max(minuten)

    # Stapgrootte van 30 minuten.
    stap = 30
    start = (minimum // stap) * stap
    einde = ((maximum // stap) + 2) * stap
    bins = list(range(start, einde, stap))

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(
        minuten,
        bins=bins,
        color=ORANJE,
        edgecolor="black",
        linewidth=0.8,
    )

    gemiddelde = sum(minuten) / len(minuten)

    ax.axvline(
        gemiddelde,
        color="black",
        linestyle="--",
        linewidth=1.5,
        label=f"Gemiddelde: {gemiddelde:.1f} minuten",
    )

    ax.set_title(
        "Weghorst-minuten: de grote nationale gok\n"
        "Van pinchhitter tot bijna onmisbare basisspeler.",
        fontsize=15,
        pad=14,
    )

    ax.set_xlabel("Voorspelde speelminuten")
    ax.set_ylabel("Aantal deelnemers")
    ax.set_xticks(bins)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()

    fig.tight_layout()

    fig.savefig(
        uitvoer_pad,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)


def main() -> int:
    try:
        kolom, waarden = lees_voorspellingen(
            CSV_PAD
        )

        maak_scatterplot(
            waarden,
            UITVOER_PAD,
        )

        maak_numerieke_verdeling(
            waarden,
            NUMERIEKE_UITVOER_PAD,
        )

    except Exception as fout:
        print(
            f"FOUT: {fout}",
            file=sys.stderr,
        )
        return 1

    print(f"Weghorst-kolom: {kolom}")
    print(f"Aantal voorspellingen: {len(waarden)}")
    print(f"Scatterplot gemaakt: {UITVOER_PAD}")
    print(
        "Numerieke verdeling gemaakt: "
        f"{NUMERIEKE_UITVOER_PAD}"
    )

    return 0




if __name__ == "__main__":
    raise SystemExit(main())