# WK Experts Poule – formulieren, CSV en website

Dit project zet lokale DOCX- en PDF-formulieren om naar één compacte CSV. De website leest daarna de voorspellingen en werkelijke uitslagen rechtstreeks uit de map `data/` en berekent de actuele stand in de browser.

## 1. Formulieren importeren

Plaats alle ingevulde formulieren lokaal in:

```text
data/formulieren/
```

Start op Windows:

```text
importeer.bat
```

Of via de terminal:

```bash
python -m pip install -r requirements.txt
python importeer_formulieren.py
```

Het script maakt of vernieuwt:

- `data/voorspellingen.csv`
- `data/kolommen.csv`
- `data/import_fouten.csv`

De vier voorspelde slechtste nummers drie staan als onderdeel van fase 1 in deze kolommen:

```text
slechtste_3_1,slechtste_3_2,slechtste_3_3,slechtste_3_4
```

Daarna volgen pas de echte bonusvragen.

## 2. Werkelijke poulestanden invullen

Open `data/uitslagen.csv` en vul bij ieder land de echte eindpositie `1`, `2`, `3` of `4` in.

```csv
poule,land,positie
A,Zuid-Afrika,4
A,Zuid-Korea,2
A,Mexico,1
A,Tsjechië,3
```

Een poule telt pas mee zodra alle vier de posities geldig en uniek zijn. Ieder land op exact de juiste plaats levert 1 punt op. Dat zijn maximaal 48 punten.

## 3. Vier slechtste nummers drie invullen

Deze voorspelling hoort bij fase 1 en is geen bonusvraag.

Open:

```text
data/slechtste_nummers_drie.csv
```

Vul daar de vier werkelijke landen in. De volgorde maakt niet uit:

```csv
nummer,land
1,Land één
2,Land twee
3,Land drie
4,Land vier
```

De website kent automatisch 3 punten toe voor ieder correct voorspeld land. Dit onderdeel is maximaal 12 punten waard. Fase 1 is dus maximaal 60 punten waard.

De vier landen tellen pas mee wanneer alle vier geldig en uniek zijn ingevuld.

## 4. Website lokaal bekijken

Dubbelklik op Windows op:

```text
start_website.bat
```

De website opent op:

```text
http://localhost:8000
```

Open `index.html` niet rechtstreeks met een dubbelklik. Browsers blokkeren dan meestal het inlezen van lokale CSV-bestanden.

Op macOS of Linux:

```bash
./start_website.sh
```

Klik in de ranglijst op een deelnemer. Je ziet dan afzonderlijk:

- alle twaalf poulevoorspellingen;
- een puntentabel voor de vier slechtste nummers drie;
- de overige bonusantwoorden.

## 5. Publiceren met GitHub Pages

Upload de projectmap naar een GitHub-repository en activeer GitHub Pages vanuit de hoofdbranch en de rootmap.

De originele DOCX- en PDF-formulieren blijven lokaal. Door `.gitignore` wordt `data/formulieren/` niet naar GitHub gestuurd. Voor de website zijn alleen de gegenereerde CSV-bestanden en de websitebestanden nodig.

Na een wijziging in bijvoorbeeld `data/uitslagen.csv` of `data/slechtste_nummers_drie.csv` berekent de website bij het herladen direct de nieuwe stand.

## Andere lokale invoermap gebruiken

```bash
python importeer_formulieren.py --invoer "D:/WK-poule/formulieren"
```
