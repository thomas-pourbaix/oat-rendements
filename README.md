# Rendement des OAT à l'échéance

Mini-application qui liste toutes les OAT (obligations de l'État français) cotées sur Euronext Paris et calcule leur **rendement annuel si on les garde jusqu'à l'échéance** (taux actuariel). On choisit un horizon de *n* ans et la page affiche les titres qui arrivent à échéance autour de cet horizon.

**En ligne : https://thomas-pourbaix.github.io/oat-rendements/**

## Fonctionnement

1. Chaque soir de semaine, une GitHub Action exécute `python -m oat.build` :
   - [oat/euronext.py](oat/euronext.py) récupère les obligations de l'émetteur « REPUBLIC OF FRANCE » et leur dernier cours via l'API JSON d'Euronext Live ;
   - [oat/figi.py](oat/figi.py) récupère le coupon et le type de chaque titre (OAT classique, OATi, OAT€i, strip) via l'API publique [OpenFIGI](https://www.openfigi.com/api) ;
   - [oat/yields.py](oat/yields.py) calcule le taux actuariel : coupon annuel, coupon couru ACT/ACT ICMA, règlement à J+2 ouvrés ;
   - le résultat est écrit dans `site/data/oats.json`.
2. Le dossier `site/` (HTML/JS statique) est publié sur GitHub Pages ; le filtrage par horizon se fait dans le navigateur.

## En local

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q
.venv/bin/python -m oat.build
python3 -m http.server 8765 -d site
```

## Limites

- Le rendement est calculé sur le **dernier cours échangé**, pas sur le prix vendeur du carnet d'ordres : sur un titre peu échangé, l'écart peut être significatif. La date du cours est affichée.
- Rendement **brut** : ni frais de courtage ni fiscalité.
- Pour les OATi / OAT€i, le rendement affiché est un rendement réel (hors inflation).
- Pas un conseil en investissement.

## Licence

Copyright (C) 2026 Thomas Pourbaix

Ce programme est un logiciel libre, distribué sous licence [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-only). Toute version modifiée mise à disposition, y compris via un service en ligne, doit publier son code source sous la même licence.
