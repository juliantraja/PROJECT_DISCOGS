# Discogs Electronic Vinyl — Notebook Plan

## Périmètre

Dataset : `data/processed/discogs_releases_electronic_20260201.csv` (3.2 GB)
Filtre   : `genres` contient "Electronic" **ET** `format_names` contient "Vinyl"
Résultat : ~1-2M releases vinyl électroniques

---

## Partie 0 — Contexte & Prérequis

- 0.0 : Contexte général
- 0.1 : Configuration système requise (Python 3.13.x)
- 0.2 : Setup environnement — Mac/Linux
- 0.3 : Setup environnement — Windows
- 0.4 : Instructions lancement notebook
- 0.5 : Vérification des versions (code)
- 0.6 : Conseils reproductibilité
- 0.7 : Vue d'ensemble des outils (tableau librairies)
- 0.8 : Justification des choix techniques

---

## Partie 1 — Objectifs

| | Question | Type |
| --- | --- | --- |
| **EDA** | Comment le vinyl électronique a-t-il évolué (décennie, pays, labels) ? | Descriptif |
| **Classification** | Peut-on distinguer un vinyl d'un format digital depuis les métadonnées ? | Supervisé |
| **Prédire & Interpréter** | Peut-on prédire la rareté/désirabilité d'une release depuis ses métadonnées ? | Supervisé + XAI |

---

## Partie 2 — Préparation des données

### 2.1 Setup & imports

```python
# Standard library
sys, os, re, warnings, time, pickle, threading, signal, atexit
collections.Counter, concurrent.futures, itertools, pathlib, io.StringIO

# Data & numerical
numpy, pandas, scipy.sparse

# Visualisation
matplotlib as mpl, matplotlib.pyplot, seaborn, plotly.express, plotly.graph_objects

# ML
sklearn : model_selection, preprocessing, compose, pipeline, impute,
          linear_model, ensemble, dummy, metrics
umap, shap

# Jupyter & API
IPython.display, ipywidgets, tqdm, requests
```

**Constantes clés :**

```python
FILTER_DECADES   = ["1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]
FILTER_YEAR_MIN  = 1970
FILTER_YEAR_MAX  = 2026
RANDOM_STATE     = 42
SAMPLE_N         = 4_850_000     # max pour la classification
TOP_STYLES_N     = 20
TOP_LABELS_N     = 20
MIN_STYLE_N      = 300           # seuil inclusion style
THEME            = "plotly_dark"
```

### 2.2 Chargement & filtrage

- Lire uniquement 12 colonnes utiles
- Filtrer : `genres.str.contains("Electronic")` + `format_names.str.contains("Vinyl")`
- Cache Pickle (`data/interim/discogs_electronic.pkl`) pour les runs suivants

**Chemins de fichiers :**

```python
DATA_PATH     = Path("../data/processed/discogs_releases_electronic_20260201.csv")
CACHE_PKL     = Path("../data/interim/discogs_electronic.pkl")
API_CACHE_PKL = Path("../data/interim/discogs_api_cache.pkl")
```

### 2.3 Diagnostic qualité (EDA initiale)

- Missing ratio sur colonnes clés
- Période couverte (min/max `released_year`)
- Top styles bruts (vérification cohérence)

### 2.4 Feature engineering

| Variable dérivée | Source | Description |
| --- | --- | --- |
| `style_first` | `styles` | 1er style |
| `style_count` | `styles` | Nombre de styles |
| `label_first` | `label_names` | 1er label |
| `label_top` | `label_first` | Top 50 labels, le reste → "Other" |
| `genre_count` | `genres` | Nombre de genres |
| `decade` | `released_year` | 1960s, 1970s, …, 2020s |
| `release_type` | `format_descriptions` | LP / EP / Single / Album / Compilation |
| `vinyl_size` | `format_descriptions` | 12" / 7" / 10" / Unknown |
| `is_limited` | `format_descriptions` | 1 si Limited Edition |
| `is_promo` | `format_descriptions` | 1 si Promo |
| `is_reissue` | `format_descriptions` | 1 si Reissue ou Repress |

### 2.5 Filtres finaux

- Filtre temporel : `released_year` entre `FILTER_YEAR_MIN` et `FILTER_YEAR_MAX`
- Filtre styles : top styles avec ≥ `MIN_STYLE_N` releases

---

## Partie 3 — EDA narrative

### 3.0x — Projection UMAP (50k releases)

```python
UMAP_SAMPLE_N    = 50_000
UMAP_MIN_DIST    = 0.05
UMAP_N_NEIGHBORS = 15
UMAP_COLOR_BY    = "released_year"  # ou "style_first", "format_cat"
```

- Réduction dimensionnelle sur features multi-label (styles encodés via MultiLabelBinarizer)
- Scatter coloré par année ou style (Plotly hover interactif)

### 3.1 — L'évolution temporelle

- **Releases par décennie** (bar chart) → creux 2000s, comeback 2010s
- **Top styles par décennie** (stacked bar) → Techno dominant 90s, Deep House stable
- **Format mix par décennie** → le 12" single domine-t-il toujours ?
- **Lifecycle des styles** (part de marché par an)

### 3.2 — La géographie

- **Top pays** (horizontal bar chart)
- **Heatmap pays × style** (normalisée par pays %) → UK → Drum n Bass, Germany → Techno
- **Trajectoires pays par décennie**

### 3.3 — Le fingerprint des grands labels

- **Top labels par volume** (bar chart, sans "Unknown"/"Not On Label")
- **Heatmap label × style** (normalisée par label %) → ADN stylistique
- **Évolution temporelle** des top labels (releases par décennie)

### 3.4 — Volumes dominants

- **Top 20 releases** par volume de pressages (`master_id`)
- **Top 20 artistes** par volume de releases

---

## Partie 4 — Classification : Vinyl vs Digital

### 4.0 Contexte

- Transition descriptif → prédictif
- **Cible** : `format_bin` — Vinyl (1) vs Digital (0) — classification binaire
- Tester si les métadonnées encodent des patterns de format physique vs digital

### 4.1 Questions & hypothèses

- Un vinyl a-t-il un profil artistique différent d'un format digital ?
- Quelles features discriminent le mieux les deux formats ?

### 4.2 Features

```python
NUM_FMT = ["artist_count", "is_limited", "is_reissue"]
CAT_FMT = ["country", "label_first", "style_first"]
```

### 4.3 Pipeline sklearn

```python
ColumnTransformer :
  num → SimpleImputer(median)
  cat → SimpleImputer(most_frequent) + OneHotEncoder(handle_unknown="ignore")

Modèles :
  DummyClassifier(stratified) → baseline
  LogisticRegression(max_iter=500, class_weight="balanced")
  RandomForestClassifier(n_estimators=120, max_depth=20, class_weight="balanced")
```

### 4.4 Évaluation

- Tableau comparatif Baseline / LR / RF (Accuracy, Macro-F1, Balanced Accuracy)
- Matrices de confusion (heatmap Plotly) → `outputs/figures/fig_cm*.html`
- Feature importances RF (top 20) → `outputs/figures/fig_imp.html`
- Séparabilité temporelle : performance du modèle année par année
- EDA profil comparatif Vinyl vs Digital

---

## Partie 5 — BONUS : Prédire & Interpréter la désirabilité

### 5.0 Contexte

- **Problème** : prédire `want_have_ratio` (proxy rareté/désirabilité) depuis les métadonnées
- **Métriques atteintes** : régression R²=0.67 · classification ROC-AUC=0.93
- Source des labels : API Discogs marketplace (`want`, `have`, `lowest_price`)

### 5.1 Constitution du dataset & cible

- Sélection du sous-ensemble vinyl électronique
- Définition de la cible `want_have_ratio = want / have` (filtre `have > 0` obligatoire)

### 5.2 Setup API Discogs

- Auth via `.env.local` (`DISCOGS_TOKEN`)
- Rate limiting : 60 req/min, `MAX_WORKERS = 5`, `DELAY = 0.5s`
- Cache persistant : `data/interim/discogs_api_cache.pkl` + `.tmp.pkl`

### 5.3 Enrichissement API

- Appel Discogs marketplace pour chaque `release_id` : `want`, `have`, `lowest_price`
- Parallélisation ThreadPoolExecutor, sauvegarde toutes `SAVE_EVERY = 50` requêtes
- Résultat : **2 139 releases enrichies**

### 5.4 Feature engineering enrichi

| Variable | Calcul | Description |
| --- | --- | --- |
| `want_have_ratio` | `want / have` | Proxy désirabilité — **cible régression** |
| `log_scarcity` | `log1p(want/have)` | Scarcité log-transformée |
| `label_avg_ratio` | mean ratio par label | Target encoding — réputation niche du label |
| `age` | `2026 - released_year` | Ancienneté de la release |
| `log_price_nm` | `log1p(lowest_price)` | Prix log-transformé |
| `price_spread` | variance prix | Dispersion prix |
| `rating_avg`, `rating_count` | API | Note communauté Discogs |
| `format_is_ep/lp/12inch/comp` | `format_descriptions` | Flags format binaires |
| styles one-hot | top 15 styles | Encodage multi-label des styles |

```python
FEATURES_BASE = [
    'age', 'log_price_nm', 'price_spread', 'log_scarcity', 'label_avg_ratio',
    'rating_avg', 'rating_count', 'track_count',
    'format_is_ep', 'format_is_lp', 'format_is_12inch', 'format_is_comp',
    'label_enc'
] + styles_one_hot  # top 15 styles encodés
TOP_N_STYLES = 15
```

### 5.5 EDA corrélations

- Heatmap de corrélation (seaborn) → `outputs/figures/fig_heatmap.html`
- Variables incluses : `log_scarcity`, `label_avg_ratio`, `age`, `log_price_nm`, etc.

### 5.6 Modélisation

- **Régression** : Ridge + RandomForestRegressor + GradientBoostingRegressor → R²=0.67
- **Classification** : RandomForestClassifier (`want_have_ratio > seuil`) → ROC-AUC=0.93
- **Résidus OOS** : `cross_val_predict` (5-fold KFold) → scatter résidus vs prédictions → `outputs/figures/fig_rt.html`

### 5.7 Interprétabilité SHAP

- `TreeExplainer` sur le RandomForestRegressor final
- 3 waterfall plots comparatifs : release **MAX** · **MÉDIANE** · **MIN** (want_have_ratio)
- `_fmt_val()` : formatage par feature (`released_year` → int, `price_nm` → 2 décimales)
- Thème sombre via `mpl.rc_context(_dark)` (sans pollution globale du kernel)

---

## Limites connues

- **Filtrage Electronic** : certaines releases multi-genres (ex. Rock|Electronic) sont incluses
- **style_first seulement** : les releases multi-styles sont simplifiées (Deep House + Techno → Deep House)
- **label_top** : les petits labels regroupés dans "Other" perdent leur spécificité
- **Snapshot** : pas d'évolution dynamique du catalogue dans le temps
- **Déséquilibre classes** : certains styles très représentés (House, Techno) vs niches (Drone, Musique Concrète)
- **Doublons de master** : un même master contribue plusieurs lignes (pressages multiples)
- **Enrichissement partiel** : seulement 2 139 releases enrichies via API → biais de sélection possible
- **want/have snapshot** : les stats marketplace varient dans le temps, non reproductibles à date fixe
