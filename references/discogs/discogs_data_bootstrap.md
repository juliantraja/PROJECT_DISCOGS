# Discogs Data Bootstrap

## 1) Credentials setup

1. Copy `.env.local.example` to `.env.local`
2. Fill your values from Discogs developer settings:
   - `DISCOGS_USER_AGENT`
   - `DISCOGS_CONSUMER_KEY`
   - `DISCOGS_CONSUMER_SECRET`
   - optional `DISCOGS_TOKEN` (required for Part 5 API enrichment)

Keep `.env.local` private and never commit it.

## 2) Releases dump → CSV (main route)

The notebook uses `data/processed/discogs_releases_electronic_20260201.csv` generated from the Discogs monthly XML dump.

Download manually from [data.discogs.com](https://data.discogs.com/) → place in `~/Downloads/`.

**Full dump filtered to Electronic genre (~1-2M releases):**

```bash
cd PROJECT_DISCOGS
python scripts/extraction/discogs_dump_releases_xml_to_csv.py \
  --input ~/Downloads/discogs_20260201_releases.xml.gz \
  --output data/processed/discogs_releases_electronic_20260201.csv \
  --genre Electronic
```

**Smoke test (first 5 000 rows only):**

```bash
python scripts/extraction/discogs_dump_releases_xml_to_csv.py \
  --input ~/Downloads/discogs_20260201_releases.xml.gz \
  --output data/interim/discogs_releases_smoke.csv \
  --limit 5000
```

**Full dump without genre filter (~17M releases):**

```bash
python scripts/extraction/discogs_dump_releases_xml_to_csv.py \
  --input ~/Downloads/discogs_20260201_releases.xml.gz \
  --output data/processed/discogs_releases_20260201.csv
```

**Expected size**: ~17 M rows unfiltered, CSV likely 15–25 GB uncompressed. Runtime ~60–90 min.

**Script parameters:**

```bash
--input PATH     (required) .xml.gz file path
--output PATH    (required) output CSV path
--genre GENRE    (optional) filter to specific genre (e.g., "Electronic")
--limit N        (optional) stop after N rows
--no-progress    (optional) disable tqdm progress bar
```

## 3) CSV schema (45 columns)

- **Core**: `release_id`, `release_status`, `title`, `country`, `released`, `released_year`, `data_quality`, `notes`
- **Master link**: `master_id`, `is_main_release`
- **Artists**: `artist_names`, `artist_ids`, `artist_anvs`, `artist_joins`, `artist_roles`, `artist_count`
- **Extra artists**: `extraartist_names`, `extraartist_ids`, `extraartist_roles`, `extraartist_count`
- **Labels**: `label_names`, `label_ids`, `label_catnos`, `label_count`
- **Formats**: `format_names`, `format_qtys`, `format_descriptions`, `format_texts`, `format_count`
- **Genres/Styles**: `genres`, `styles`
- **Tracklist**: `track_count`, `track_positions`, `track_titles`, `track_durations`
- **Images**: `image_count`
- **Identifiers**: `barcode`, `identifier_types`, `identifier_values`
- **Videos**: `video_count`, `has_videos`, `video_srcs`
- **Companies**: `company_names`, `company_ids`, `company_roles`

List-valued fields use `|` as separator. Any `|` found in raw values is replaced with `/`.

## 4) Minimum dataset profile before modeling

- Number of rows / columns
- Missing values ratio
- Duplicate rate
- Distribution of key fields (`released_year`, `genres`, `styles`, `country`)
- Candidate target variable and business objective
