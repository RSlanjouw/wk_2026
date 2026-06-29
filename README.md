# Fase 2 update

## Installeren

```powershell
pip install -r .\requirements_fase2.txt
```

## Importeren

```powershell
python .\importeer_fase2_formulieren.py
```

Het script leest `.docx` en `.pdf` uit `data/fase2/formulieren/`.

Belangrijk:

- een unieke voornaam matcht automatisch, bijvoorbeeld `Sander` naar `Sander Stok`;
- een leeg voorspeld resultaat is toegestaan en levert 0 punten op;
- een gelijkspel zonder penaltywinnaar geeft INFO en kan maximaal 3 punten opleveren;
- geldige formulieren worden altijd opgeslagen, ook als een ander formulier een fout bevat;
- bij opnieuw importeren worden alleen de 16 regels van die deelnemer vervangen;
- bestaande voorspellingen van andere deelnemers blijven behouden;
- wanneer meerdere geldige formulieren voor dezelfde deelnemer aanwezig zijn, wint het laatst gewijzigde bestand.
