# WK Experts Poule 2026

## Pagina's

- `fase1.html`: poulefase
- `index.html`: fase 2, zestiende finales
- `fase3.html`: fase 3, achtste finales t/m finale

## Fase 3 voorbereiden

1. Werk eerst de totaalscore tot en met fase 2 bij:

```powershell
python .\genereer_punten_tot_fase2.py
```

2. Zet alle fase-3-formulieren in:

```text
data/fase3/formulieren/
```

3. Importeer DOCX en tekst-PDF:

```powershell
python .\importeer_fase3_formulieren.py
```

4. Vul werkelijke teams en uitslagen in:

```text
data/fase3/uitslagen_fase3.csv
```

5. Test lokaal:

```powershell
python -m http.server 8000
```

Open `http://localhost:8000/fase3.html`.

## Fase-3-puntentelling

- Achtste finale: 4 resultaat, 6 exact.
- Kwartfinale juiste landen: 5 resultaat, 8 exact.
- Kwartfinale verkeerde landen: 2 resultaat, 4 exact.
- Halve finale juiste landen: 6 resultaat, 10 exact.
- Halve finale verkeerde landen: 3 resultaat, 5 exact.
- Finale: 8 resultaat, 12 exact, alleen met beide juiste finalisten.
- Penaltywinnaar telt niet mee.

De pagina toont per deelnemer de voorspelde kwartfinalisten, halvefinalisten en finalisten.
