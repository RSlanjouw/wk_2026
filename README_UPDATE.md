# Fase 2 update

- DOCX en tekst-PDF worden ingelezen.
- Een unieke voornaam matcht automatisch: `Sander` wordt `Sander Stok`.
- Een lege score is toegestaan en levert 0 punten op.
- Een gelijkspel zonder penaltywinnaar geeft INFO in plaats van FOUT.
- Zo'n voorspelling kan maximaal 3 punten opleveren.

Installeren:

```powershell
pip install -r requirements_fase2.txt
```

Daarna:

```powershell
python .\importeer_fase2_formulieren.py
```
