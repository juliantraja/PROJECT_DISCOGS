# Discogs Electronic Vinyl — Plan de présentation 10 min

## Slide 1 — Contexte & objectif (1 min)

- Discogs : encyclopédie mondiale du vinyl physique — 17M releases
- Périmètre : **Electronic + Vinyl uniquement** (~1-2M releases)
- Trois questions : évolution temporelle · vinyl vs digital · prédiction de désirabilité
- Motivation personnelle : la musique électronique et le vinyl comme terrain d'analyse

## Slide 2 — Source de données & extraction (1 min)

- Dump XML public Discogs (01/02/2026) → parsing streaming → CSV (3.2 GB)
- Filtrage : `genres` = Electronic + `format_names` = Vinyl
- 12 colonnes utiles sur 45
- Feature engineering : `style_first`, `decade`, `label_top`, `vinyl_size`, `release_type`

## Slide 3 — EDA : projection UMAP + évolution temporelle (1.5 min)

- UMAP 50k releases — colorié par année ou style → clusters visuels naturels
- Évolution par décennie → creux 2000s, comeback 2010s confirmé
- Top styles par décennie (stacked bar) : Techno, House, Deep House, Drum n Bass…
- Le 12" single reste dominant sur toute la période

## Slide 4 — EDA : géographie & labels (1 min)

- Heatmap pays × style → UK → Drum n Bass / Jungle, Germany → Techno, US → House
- Fingerprint des grands labels : Warp, Kompakt, Ninja Tune, Tresor…
- Les données confirment les patterns culturels connus

## Slide 5 — Classification : Vinyl vs Digital (1.5 min)

- **Cible** : `format_bin` — Vinyl (1) vs Digital (0) — classification binaire
- **Features** : `country`, `label_first`, `style_first`, `artist_count`, `is_limited`, `is_reissue`
- Pipeline sklearn (OHE + imputation + classificateur)
- Résultats : tableau Baseline / Logistic Regression / Random Forest
- Séparabilité temporelle : performance du modèle année par année

## Slide 6 — Prédire la désirabilité : enrichissement API + modélisation (2 min)

- **Problème** : prédire `want_have_ratio` (proxy de rareté/désirabilité) depuis les métadonnées
- **Enrichissement** : appel API Discogs sur 2 139 releases → `want`, `have`, `lowest_price`
- **Features clés** : `log_scarcity`, `label_avg_ratio`, `age`, `log_price_nm`, `rating_avg`
- **Modèles** : Ridge + RandomForestRegressor + GradientBoostingRegressor
- **Résultats** : régression R²=0.67 · classification ROC-AUC=0.93
- **Résidus OOS** : `cross_val_predict` 5-fold — diagnostic d'overfitting

## Slide 7 — SHAP : interpréter les prédictions (1.5 min)

- `TreeExplainer` sur RandomForestRegressor final
- 3 waterfall plots : release MAX · MÉDIANE · MIN (want_have_ratio)
- `log_scarcity` et `label_avg_ratio` dominent les contributions SHAP
- Interprétation concrète : "label niche + peu d'exemplaires dispo → forte désirabilité"

## Slide 8 — Limites & prochaines étapes (1 min)

- `style_first` seulement : nuance multi-style perdue
- Snapshot catalogue — want/have varient dans le temps, non reproductibles
- Enrichissement partiel (2 139 / ~1-2M) → biais de sélection possible
- Prochaines étapes : élargir l'enrichissement API, validation temporelle, TF-IDF multi-label

## Q&A backup

- Distribution des styles (top 20)
- Variables dérivées (lexique technique)
- Distribution géographique détaillée
- Métriques complètes par classe (precision / recall / F1)
- Détail pipeline enrichissement API (rate limiting, cache, ThreadPoolExecutor)
- Choix UMAP vs PCA (métrique Jaccard, données multi-label sparse)
