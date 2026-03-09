# Discogs Electronic — Plan de présentation 10 min

~10 slides · 1 min moyenne par slide

---

## Slide 1 — Titre (30 s)

**Titre** : *Discogs Electronic — Analyse de données, modélisation et collectabilité*

- Nom, formation Le Wagon · Python & Machine Learning
- Date : Jeudi 19 Mars 2026
- *"Qu'est-ce qui fait qu'un vinyl vaut de l'or — et peut-on le prédire ?"*

---

## Slide 2 — Motivation & sujet (1 min)

- **Discogs** : plus grande base de données collaborative de musique physique — 17M releases
- *"La musique électronique n'est pas un genre — c'est un écosystème."*
  Des labels qui pressent à 300 exemplaires · des vinyls à 200 € vingt ans après · des styles qui remodelent un genre
- **Pourquoi ce sujet ?**
  Cas réel, riche et imparfait — à l'opposé d'un dataset de cours.
  Chaque ligne = une **release** (pressage précis), pas une œuvre abstraite → granularité rare pour analyser simultanément styles, formats, pays, labels et désirabilité
- **3 questions** : Comment est structuré le catalogue ? Qu'est-ce qui sépare Vinyl et Digital ? Peut-on prédire la collectabilité ?

---

## Slide 3 — Source & pipeline de données (1 min)

- **Source** : Dump XML public Discogs · snapshot **01/02/2026**
**Pipeline** :

```text
XML dump Discogs (~17M releases)
  └── Filtre genre "Electronic"    → 4,85M releases
      └── Parsing streaming gzip   → CSV 3.2 GB · 45 colonnes
          └── Cache pickle         → chargement ~3 s
```

- **Ce qu'on garde** : 23 colonnes · `release_id`, `title`, `artists`, `label`, `country`, `styles`, `format_names`, `year`, `want`, `have`, `lowest_price`
- **Feature engineering** : `style_first` · `label_first` · `format_cat` · `is_vinyl` · `decade` · `is_limited` · `is_reissue` · `release_type`

---

## Slide 4 — EDA : évolution temporelle & styles (1 min)

- **Creux 2000s** : montée du CD et du Digital → part Vinyl à son minimum
- **Comeback vinyl 2010s** : confirmé dans les données — tendance inverse depuis 2012
- **Styles par décennie** (stacked bar) :
  - Années 90 : Techno · House · Jungle · Drum n Bass
  - Années 2000 : Deep House · Minimal · Progressive
  - Années 2010+ : Techno · House · Ambient revient
- Le **12" single** reste le format physique dominant sur toute la période

---

## Slide 5 — EDA : géographie & labels (45 s)

- **Heatmap pays × style** :
  - 🇬🇧 UK → Drum n Bass / Jungle
  - 🇩🇪 Allemagne → Techno
  - 🇺🇸 US → House / Deep House
  - 🇷🇺 URSS/Russie → Vinyl quasi-exclusif
- **Fingerprint labels** : Warp · Kompakt · Ninja Tune · Tresor — profils stylistiques stables et identifiables dans les données
- *Les données confirment ce que les amateurs de musique savent intuitivement — et permettent de le quantifier*

---

## Slide 6 — Classification : Vinyl vs Digital (1.5 min)

- **Question** : les métadonnées seules permettent-elles de distinguer un vinyl d'une release digitale ?
- **Setup** : 2,98M releases · cible `format_bin` · 6 features (`country`, `label_first`, `style_first`, `artist_count`, `is_limited`, `is_reissue`) · **aucune info directe sur le format physique**
- **Résultats** :

| Modèle | Balanced Accuracy | vs Baseline |
| --- | --- | --- |
| Dummy (baseline) | 0.500 | — |
| **★ LogReg** | **0.832** | **+33 pp** |
| RandomForest | 0.752 | +25 pp |

- **Validation temporelle (1999–2024)** :
  - Stable entre **0.70 et 0.80** sur 25 ans
  - Creux **2009 : 0.704** — coexistence maximale Vinyl/Digital
  - Signal stable à **~0.80** depuis 2013, bande d'incertitude étroite
- **Conclusion** : *La séparation est structurelle, portée par le label et le pays. Le marché s'est re-stratifié : Vinyl = collector/DJ · Digital = tout le reste.*

---

## Slide 7 — Enrichissement API Discogs (45 s)

- **Problème** : le CSV ne contient pas les signaux marchands (`want`, `have`, prix actuel)
- **Solution** : enrichissement via API Discogs sur un sous-ensemble de vinyls ciblés
- **Données collectées** : `want` · `have` · `lowest_price` · `rating_avg` · `rating_count` · `num_for_sale`
- **Contraintes traitées** : rate limiting (1 req/s) · cache `.pkl` résumable · ThreadPoolExecutor · sauvegarde d'urgence en cas d'interruption
- **Résultat** : **2 139 releases** enrichies · variable cible `want_have_ratio` = proxy de rareté et de désirabilité

---

## Slide 8 — Modélisation : prédire la collectabilité (1 min)

**Régression** — prédire `want_have_ratio` (CV 5-fold) :

| Modèle | R² | MAE |
| --- | --- | --- |
| Ridge (baseline) | 0.415 | 0.833 |
| **★ RandomForest** | **0.674** | **0.519** |
| GradientBoosting | 0.643 | 0.548 |

**Classification** — prédire `is_collectible` (CV 5-fold) :

| Modèle | Bal. Accuracy | ROC-AUC |
| --- | --- | --- |
| RidgeClf | 0.781 | 0.855 |
| RandomForest | 0.838 | 0.921 |
| **★ GradientBoosting** | **0.844** | **0.921** |

- *67% de variance expliquée · 84% de Balanced Accuracy · ROC-AUC = 0.921*
- *Il y a un signal réel et mesurable dans les métadonnées d'une release*

---

## Slide 9 — SHAP : ce qui fait qu'un vinyl vaut de l'or (1.5 min)

- **`TreeExplainer`** sur RandomForestRegressor · Summary bar + beeswarm + 3 waterfall plots
- **Facteurs dominants** : `log_scarcity` (rareté brute) · `label_avg_ratio` (réputation du label) · `age` · `log_price_nm`

**3 cas concrets** :

| | Release | Label | Année | Ratio | Prix |
| --- | --- | --- | --- | --- | --- |
| 🔺 MAX | Baby Pop — *Minimal Structures* | Tetrode Music | 1996 | **29.26** | 178 € |
| ➖ Médiane | Martinez — *Skywalker EP* | Dessous Recordings | 2003 | 0.81 | 22 € |
| 🔻 MIN | Schneider & Aera — *Taylor & Smith EP* | Circus Company | 2011 | 0.00 | 6 € |

- **Conclusion** : *Label de niche + rareté + ancienneté → forte désirabilité.*
  *Un vinyl récent sur un grand label ne collecte pas.*

---

## Slide 10 — Synthèse & limites (1 min)

**3 réponses aux 3 questions** :

1. **Structure du catalogue** → patterns culturels robustes et mesurables (UK/Drum n Bass, Allemagne/Techno, comeback vinyl 2010s)
2. **Vinyl vs Digital** → séparation structurelle · 83% Bal. Accuracy · stable sur 25 ans · portée par label + pays
3. **Collectabilité** → 67% de variance expliquée · label de niche + rareté + ancienneté = les 3 signaux dominants

**Limites honnêtes** :

- Enrichissement partiel (2 139 / 4,85M) → biais de sélection possible
- Snapshot Discogs (01/02/2026) — want/have varient dans le temps
- `style_first` seulement → nuance multi-style perdue

**Prochaines étapes** : élargir l'enrichissement API · validation temporelle Partie 5 · TF-IDF multi-label

---

## Q&A backup

- Distribution des styles (top 20) et évolution décennale
- Pourquoi LogReg > RandomForest en Partie 4 ? *(régularisation + données sparse OHE)*
- Pourquoi GBR > RF en classification Partie 5 ? *(boosting séquentiel, dataset ~2 139 lignes)*
- Choix UMAP vs PCA *(métrique Jaccard, données multi-label sparse)*
- Détail pipeline API *(rate limiting · ThreadPoolExecutor · sauvegarde urgence)*
- Métriques complètes par classe *(precision · recall · F1)*
- Lexique variables dérivées
