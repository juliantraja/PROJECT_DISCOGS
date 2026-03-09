# PROJECT_DISCOGS

Analyse de données Discogs — marché de la musique électronique (environ 4,85 millions de sorties).
Le projet est divisé en 5 parties analytiques : exploration, nettoyage, visualisation, modélisation et enrichissement API.

---

## Structure du projet

```text
PROJECT_DISCOGS/
├── data/
│   ├── raw/                 # fichiers sources téléchargés (.xml.gz)
│   ├── interim/             # caches de traitement (discogs_electronic.pkl, discogs_api_cache.pkl)
│   └── processed/           # dataset principal (discogs_releases_electronic_20260201.csv)
├── notebooks/               # notebook principal + plan
├── outputs/
│   └── figures/             # graphiques Plotly exportés en HTML
├── reports/                 # plan de présentation
├── scripts/
│   └── extraction/          # parseur du dump XML Discogs
├── references/              # guides, dictionnaires, notes de projet
├── .env.local.example       # modèle de fichier de configuration (sans secrets)
└── requirements.txt         # liste des dépendances Python
```

---

## Mise en place (première utilisation)

Suivre les étapes dans l'ordre. Chaque étape est expliquée ci-dessous.

### Étape 1 — Télécharger les fichiers de données

Les fichiers volumineux ne sont pas inclus dans ce dépôt GitHub (trop lourds). Il faut les télécharger séparément depuis Google Drive et les placer dans les répertoires indiqués.

| Fichier | Taille | Où le placer | Téléchargement |
| --- | --- | --- | --- |
| `discogs_releases_electronic_20260201.csv` | 3.2 Go | `data/processed/` | [Google Drive](https://drive.google.com/file/d/1fMLlL0iKZ2PcEA02EdpK6VmYe68Jpj7b/view?usp=drive_link) |
| `discogs_electronic.pkl` | 1.4 Go | `data/interim/` | [Google Drive](https://drive.google.com/file/d/1-mIhUng0hQgZThnKutWRfa66DPSWJuRb/view?usp=drive_link) |
| `discogs_api_cache.pkl` | 312 Ko | `data/interim/` | [Google Drive](https://drive.google.com/file/d/1rJzEAO5gSimokoLDk3hwN57vl3nPsazX/view?usp=drive_link) |
| `.env.local` | — | racine du projet | [Google Drive](https://drive.google.com/file/d/1gL8dASiGonydDwV0AQIn-GO8X00g_dkA/view?usp=drive_link) *(lien privé)* |

**Explications :**

- **`discogs_releases_electronic_20260201.csv`** : le dataset principal, indispensable pour démarrer. Sans ce fichier, le notebook ne peut pas s'exécuter.
- **`discogs_electronic.pkl`** : un cache généré automatiquement à la fin de la Partie 2 à partir du CSV. Si vous avez le CSV, ce fichier sera recréé tout seul lors du premier lancement — vous n'avez donc pas besoin de le télécharger obligatoirement.
- **`discogs_api_cache.pkl`** : contient les résultats de l'enrichissement API Discogs (2 139 sorties). Nécessaire uniquement pour la **Partie 5**. Permet d'éviter de refaire tous les appels API.
- **`.env.local`** : contient les clés API Discogs (secrets). Nécessaire uniquement pour la **Partie 5**. Sans ce fichier, les Parties 1 à 4 fonctionnent normalement.

> **Comment placer les fichiers ?** Après téléchargement, déplacer chaque fichier dans le dossier indiqué dans la colonne "Où le placer", à l'intérieur du dossier `PROJECT_DISCOGS`.

---

### Étape 2 — Vérifier que Python est installé

Ce projet nécessite **Python 3.13** (version recommandée : `3.13.11`).

Pour vérifier votre version, ouvrir un terminal et taper :

```bash
python3 --version
```

Si Python n'est pas installé ou si votre version est trop ancienne, le télécharger sur [python.org](https://www.python.org/downloads/).

---

### Étape 3 — Créer l'environnement et installer les dépendances

Un environnement virtuel permet d'installer les librairies Python du projet sans affecter le reste de votre système.

**Sur Mac / Linux** — ouvrir le Terminal et exécuter chaque ligne :

```bash
# Aller dans le dossier du projet
cd /chemin/vers/PROJECT_DISCOGS

# Créer l'environnement virtuel (une seule fois)
python3 -m venv .venv

# Activer l'environnement (à faire à chaque nouvelle session de terminal)
source .venv/bin/activate

# Mettre pip à jour
python -m pip install --upgrade pip

# Installer toutes les librairies nécessaires
pip install -r requirements.txt

# Enregistrer l'environnement comme kernel Jupyter (une seule fois)
python -m ipykernel install --user --name discogs-env --display-name "Python (discogs-env)"
```

**Sur Windows** — ouvrir PowerShell et exécuter chaque ligne :

```powershell
# Aller dans le dossier du projet
cd C:\chemin\vers\PROJECT_DISCOGS

# Créer l'environnement virtuel (une seule fois)
py -3.13 -m venv .venv

# Activer l'environnement (à faire à chaque nouvelle session)
.\.venv\Scripts\Activate.ps1

# Mettre pip à jour
python -m pip install --upgrade pip

# Installer toutes les librairies nécessaires
pip install -r requirements.txt

# Enregistrer l'environnement comme kernel Jupyter (une seule fois)
python -m ipykernel install --user --name discogs-env --display-name "Python (discogs-env)"
```

> Si PowerShell bloque l'activation du script `.ps1`, exécuter d'abord : `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

### Étape 4 — Lancer le notebook

Depuis le terminal, avec l'environnement activé :

```bash
# Se placer à la racine du projet
cd /chemin/vers/PROJECT_DISCOGS

# Lancer JupyterLab
jupyter lab
```

JupyterLab s'ouvre dans votre navigateur. Dans le panneau de gauche, naviguer vers `notebooks/` et ouvrir `project_discogs.ipynb`.

**Sélectionner le bon kernel :** en haut à droite du notebook, cliquer sur le nom du kernel et choisir **`Python (discogs-env)`**. Si ce kernel n'apparaît pas, relancer la commande `ipykernel install` de l'Étape 3.

Exécuter les cellules dans l'ordre (menu **Run → Run All Cells** recommandé au premier lancement).

---

## Régénérer les données depuis le dump XML (avancé)

Si vous souhaitez recréer le CSV à partir des données sources Discogs :

1. Télécharger `discogs_20260201_releases.xml.gz` depuis [data.discogs.com](https://data.discogs.com/) ou directement ici [LIEN](https://data.discogs.com/?download=data%2F2026%2Fdiscogs_20260201_releases.xml.gz)
2. Lancer le parseur :

```bash
python scripts/extraction/discogs_dump_releases_xml_to_csv.py \
  --input ~/Downloads/discogs_20260201_releases.xml.gz \
  --output data/processed/discogs_releases_electronic_20260201.csv \
  --genre Electronic
```

Pour un test rapide sur 5 000 lignes :

```bash
python scripts/extraction/discogs_dump_releases_xml_to_csv.py \
  --input ~/Downloads/discogs_20260201_releases.xml.gz \
  --output data/interim/discogs_releases_smoke.csv \
  --limit 5000
```

Voir `references/discogs/discogs_data_bootstrap.md` pour le schéma complet et les instructions détaillées.

---

## Notes

- `discogs_electronic.pkl` est régénéré automatiquement si absent — inutile de le télécharger si vous avez le CSV.
- `discogs_api_cache.pkl` (312 Ko) permet de sauter les appels API en Partie 5 — le télécharger pour éviter le rate limiting Discogs.
