# Fase 2 gebruiken

## Mappenstructuur

```text
index.html
fase1.html
fase2.css
fase2.js
importeer_fase2_formulieren.py

data/
└── fase2/
    ├── fase1_punten.csv
    ├── voorspellingen_fase2.csv
    ├── uitslagen_fase2.csv
    └── formulieren/
        ├── formulier_tigo.docx
        ├── formulier_jannetta.docx
        └── formulier_jonah.docx
```

## Formulieren importeren

Installeer eenmalig:

```powershell
pip install python-docx
```

Voer daarna vanuit de repository-root uit:

```powershell
python .\importeer_fase2_formulieren.py
```

Het script controleert:

- of de naam in `fase1_punten.csv` voorkomt;
- of alle 16 wedstrijden aanwezig zijn;
- of doelpunten geldige getallen zijn;
- of bij een gelijkspel een penaltywinnaar is ingevuld;
- of niet twee formulieren voor dezelfde deelnemer bestaan.

De uitvoer komt in:

```text
data/fase2/voorspellingen_fase2.csv
```

## Naam matching

De naam uit het formulier moet overeenkomen met de kolom `naam` in
`fase1_punten.csv`.

Hoofdletters, accenten, leestekens en dubbele spaties worden genegeerd.
`Jonah van Emden` en `jonah  van-emden` matchen dus met elkaar.

Een naam die echt anders is, zoals `Ruben` terwijl alleen Tigo, Jannetta en
Jonah in de CSV staan, wordt bewust geweigerd.

## Uitslagen invoeren

Vul gespeelde wedstrijden in `data/fase2/uitslagen_fase2.csv` in:

```csv
wedstrijd,thuis,werkelijk_thuis,uit,werkelijk_uit,winnaar_na_penalties
1,Zuid-Afrika,1,Canada,2,
14,Australië,2,Egypte,2,Egypte
```

Laat `werkelijk_thuis` en `werkelijk_uit` leeg zolang een wedstrijd niet is
verwerkt.

## Lokaal testen

Gebruik een lokale webserver:

```powershell
python -m http.server 8000
```

Open daarna:

```text
http://localhost:8000/
```
