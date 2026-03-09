#!/usr/bin/env python3
"""
Parse Discogs *releases* XML dump (.xml.gz) → flat CSV with all available fields.

List-valued fields (artists, labels, tracks, …) use pipe ( | ) as separator.
Any pipe character found inside a raw value is replaced with / before joining
so that the separator is unambiguous.

Schema – 45 columns:
  release_id, release_status
  title, country, released, released_year, data_quality, notes
  master_id, is_main_release
  artist_names, artist_ids, artist_anvs, artist_joins, artist_roles, artist_count
  extraartist_names, extraartist_ids, extraartist_roles, extraartist_count
  label_names, label_ids, label_catnos, label_count
  format_names, format_qtys, format_descriptions, format_texts, format_count
  genres, styles
  track_count, track_positions, track_titles, track_durations
  image_count
  barcode, identifier_types, identifier_values
  video_count, has_videos, video_srcs
  company_names, company_ids, company_roles

Usage:
  # Run from PROJECT_DISCOGS/ (project root):
  python scripts/extraction/discogs_dump_releases_xml_to_csv.py \
    --input ~/Downloads/discogs_20260201_releases.xml.gz \
    --output data/processed/discogs_releases_20260201.csv

  # Electronic only (recommended for the vinyl electronic project):
  python scripts/extraction/discogs_dump_releases_xml_to_csv.py \
    --input ~/Downloads/discogs_20260201_releases.xml.gz \
    --output data/processed/discogs_releases_electronic_20260201.csv \
    --genre Electronic

  Note: --no-capture-output is required for the live progress bar to display.

Options:
  --limit N        Stop after N rows written (default: 0 = no cap). Useful for quick tests.
  --genre GENRE    Keep only releases whose <genres> list contains GENRE (case-sensitive).
                   Default: "" (no filter, export everything).
  --no-progress    Disable real-time progress bar.

Notes:
  - Track-level artist credits (compilations) are not expanded per track;
    use release-level artist_names for that signal.
  - Sub-tracks (nested inside a track) are not expanded; only top-level tracks.
  - Image and video URIs from Discogs public dumps are typically empty strings
    in the data files; image_count and video_srcs capture what is present.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import re
import sys
import time
import xml.etree.ElementTree as ET
from io import BufferedIOBase
from pathlib import Path

try:
    from tqdm import tqdm as _tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


RELEASE_FIELDS = [
    # ── core identifiers ────────────────────────────────────────────────────
    "release_id",
    "release_status",
    # ── release metadata ────────────────────────────────────────────────────
    "title",
    "country",
    "released",          # raw date string (e.g. "1999-00-00", "2001", "2003-06")
    "released_year",     # 4-digit integer year extracted from released
    "data_quality",
    "notes",
    # ── master link ─────────────────────────────────────────────────────────
    "master_id",
    "is_main_release",   # "true" / "false" / ""
    # ── main artists ────────────────────────────────────────────────────────
    "artist_names",      # pipe-sep canonical names
    "artist_ids",        # pipe-sep Discogs artist IDs
    "artist_anvs",       # pipe-sep "as named value" (credited name, may differ from canonical)
    "artist_joins",      # pipe-sep join words between artists (",", "&", "And", …)
    "artist_roles",      # pipe-sep roles (usually empty for main artists)
    "artist_count",
    # ── extra / credited artists ────────────────────────────────────────────
    "extraartist_names",
    "extraartist_ids",
    "extraartist_roles", # e.g. "Remix", "Mastered By", "Photography By"
    "extraartist_count",
    # ── labels ──────────────────────────────────────────────────────────────
    "label_names",       # pipe-sep (unique)
    "label_ids",         # pipe-sep
    "label_catnos",      # pipe-sep catalog numbers
    "label_count",
    # ── formats ─────────────────────────────────────────────────────────────
    "format_names",      # pipe-sep (e.g. "Vinyl|CD")
    "format_qtys",       # pipe-sep quantities per format
    "format_descriptions", # pipe-sep all <description> values across all formats
    "format_texts",      # pipe-sep free-text format notes
    "format_count",
    # ── genres / styles ─────────────────────────────────────────────────────
    "genres",
    "styles",
    # ── tracklist ───────────────────────────────────────────────────────────
    "track_count",
    "track_positions",   # pipe-sep (e.g. "A1|A2|B1|B2")
    "track_titles",      # pipe-sep
    "track_durations",   # pipe-sep (e.g. "6:06|4:14|5:45|8:14")
    # ── images ──────────────────────────────────────────────────────────────
    "image_count",
    # ── identifiers ─────────────────────────────────────────────────────────
    "barcode",           # first barcode value found, or ""
    "identifier_types",  # pipe-sep all identifier type strings
    "identifier_values", # pipe-sep all identifier values (parallel with types)
    # ── videos ──────────────────────────────────────────────────────────────
    "video_count",
    "has_videos",        # "1" / "0"
    "video_srcs",        # pipe-sep YouTube / external URLs
    # ── companies ───────────────────────────────────────────────────────────
    "company_names",
    "company_ids",
    "company_roles",     # entity_type_name (e.g. "Pressed By", "Distributed By")
]


# ── text helpers ─────────────────────────────────────────────────────────────

def clean(value: str) -> str:
    """Normalise whitespace, strip newlines/tabs, replace | with / to protect separator."""
    if not value:
        return ""
    v = re.sub(r"\s+", " ", value).strip()
    return v.replace("|", "/")


def node_text(node: ET.Element | None, tag: str, default: str = "") -> str:
    if node is None:
        return default
    child = node.find(tag)
    if child is None or child.text is None:
        return default
    return clean(child.text)


def attr(node: ET.Element, key: str, default: str = "") -> str:
    v = node.attrib.get(key, default)
    return clean(v) if v else default


def join_pipe(values: list[str]) -> str:
    """Join non-empty values with | (order preserved, duplicates kept — e.g. tracks)."""
    return "|".join(v for v in values if v)


def join_unique_pipe(values: list[str]) -> str:
    """Join unique non-empty values with | (order preserved)."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return "|".join(out)


def release_has_genre(elem: ET.Element, genre: str) -> bool:
    """Return True if any <genre> text in the element matches *genre* exactly."""
    return any(
        g.text and g.text.strip() == genre
        for g in elem.findall("./genres/genre")
    )


def extract_year(released: str) -> str:
    """Return the 4-digit year from strings like '1999', '1999-00-00', '2001-06'."""
    if not released:
        return ""
    m = re.match(r"(\d{4})", released.strip())
    return m.group(1) if m else ""


# ── streaming XML wrapper ────────────────────────────────────────────────────

class RootWrappedStream(BufferedIOBase):
    """
    Wrap a byte stream with a synthetic <root> element and sanitise
    invalid XML 1.0 control characters.

    Discogs dumps may lack a single XML root; wrapping solves that.
    """

    def __init__(self, base_stream: BufferedIOBase) -> None:
        self.base_stream = base_stream
        self._buffer = bytearray()
        self._stage = 0  # 0=prefix, 1=base, 2=suffix, 3=done
        self._prefix = b"<root>"
        self._suffix = b"</root>"
        invalid = list(range(0x00, 0x09)) + [0x0B, 0x0C] + list(range(0x0E, 0x20))
        self._invalid_xml_delete = bytes(invalid)

    def readable(self) -> bool:
        return True

    def _pump(self) -> bool:
        if self._stage == 0:
            self._buffer.extend(self._prefix)
            self._stage = 1
            return True
        if self._stage == 1:
            chunk = self.base_stream.read(65536)
            if chunk:
                chunk = chunk.translate(None, self._invalid_xml_delete)
                self._buffer.extend(chunk)
                return True
            self._stage = 2
            return self._pump()
        if self._stage == 2:
            self._buffer.extend(self._suffix)
            self._stage = 3
            return True
        return False

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            while self._pump():
                pass
            out = bytes(self._buffer)
            self._buffer.clear()
            return out
        while len(self._buffer) < size and self._pump():
            pass
        out = bytes(self._buffer[:size])
        del self._buffer[:size]
        return out


# ── element iterator ─────────────────────────────────────────────────────────

def iter_release_elements(in_path: Path):
    """Yield (release_elem, compressed_bytes_read, total_compressed_bytes)."""
    total_bytes = in_path.stat().st_size
    with in_path.open("rb") as raw_stream:
        with gzip.GzipFile(fileobj=raw_stream, mode="rb") as gz_stream:
            wrapped = RootWrappedStream(gz_stream)
            context = ET.iterparse(wrapped, events=("end",))
            for _, elem in context:
                if elem.tag == "release":
                    yield elem, raw_stream.tell(), total_bytes


# ── release parser ───────────────────────────────────────────────────────────

def parse_release(elem: ET.Element) -> dict[str, str]:
    # ── core ──────────────────────────────────────────────────────────────
    released_raw = node_text(elem, "released")
    master_node = elem.find("master_id")
    master_id_val = (
        clean(master_node.text) if master_node is not None and master_node.text else ""
    )
    is_main = attr(master_node, "is_main_release") if master_node is not None else ""

    # ── main artists ──────────────────────────────────────────────────────
    a_names, a_ids, a_anvs, a_joins, a_roles = [], [], [], [], []
    for a in elem.findall("./artists/artist"):
        a_names.append(node_text(a, "name"))
        a_ids.append(node_text(a, "id"))
        a_anvs.append(node_text(a, "anv"))
        a_joins.append(node_text(a, "join"))
        a_roles.append(node_text(a, "role"))

    # ── extra artists ─────────────────────────────────────────────────────
    ea_names, ea_ids, ea_roles = [], [], []
    for ea in elem.findall("./extraartists/artist"):
        ea_names.append(node_text(ea, "name"))
        ea_ids.append(node_text(ea, "id"))
        ea_roles.append(node_text(ea, "role"))

    # ── labels ────────────────────────────────────────────────────────────
    l_names, l_ids, l_catnos = [], [], []
    for lbl in elem.findall("./labels/label"):
        l_names.append(clean(lbl.attrib.get("name", "")))
        l_ids.append(clean(lbl.attrib.get("id", "")))
        l_catnos.append(clean(lbl.attrib.get("catno", "")))

    # ── formats ───────────────────────────────────────────────────────────
    f_names, f_qtys, f_descs, f_texts = [], [], [], []
    for fmt in elem.findall("./formats/format"):
        f_names.append(clean(fmt.attrib.get("name", "")))
        f_qtys.append(clean(fmt.attrib.get("qty", "")))
        f_texts.append(clean(fmt.attrib.get("text", "")))
        for d in fmt.findall("./descriptions/description"):
            if d.text:
                f_descs.append(clean(d.text))

    # ── genres / styles ───────────────────────────────────────────────────
    genres = [clean(g.text) for g in elem.findall("./genres/genre") if g.text]
    styles = [clean(s.text) for s in elem.findall("./styles/style") if s.text]

    # ── tracklist ─────────────────────────────────────────────────────────
    t_positions, t_titles, t_durations = [], [], []
    for track in elem.findall("./tracklist/track"):
        t_positions.append(node_text(track, "position"))
        t_titles.append(node_text(track, "title"))
        t_durations.append(node_text(track, "duration"))

    # ── images ────────────────────────────────────────────────────────────
    image_count = len(elem.findall("./images/image"))

    # ── identifiers ───────────────────────────────────────────────────────
    id_types, id_values = [], []
    barcode = ""
    for ident in elem.findall("./identifiers/identifier"):
        itype = clean(ident.attrib.get("type", ""))
        ivalue = clean(ident.attrib.get("value", ""))
        id_types.append(itype)
        id_values.append(ivalue)
        if not barcode and itype == "Barcode":
            barcode = ivalue

    # ── videos ────────────────────────────────────────────────────────────
    video_nodes = elem.findall("./videos/video")
    video_count = len(video_nodes)
    v_srcs = [clean(v.attrib.get("src", "")) for v in video_nodes]

    # ── companies ─────────────────────────────────────────────────────────
    co_names, co_ids, co_roles = [], [], []
    for co in elem.findall("./companies/company"):
        co_names.append(node_text(co, "name"))
        co_ids.append(node_text(co, "id"))
        co_roles.append(node_text(co, "entity_type_name"))

    return {
        "release_id":           attr(elem, "id"),
        "release_status":       attr(elem, "status"),
        "title":                node_text(elem, "title"),
        "country":              node_text(elem, "country"),
        "released":             released_raw,
        "released_year":        extract_year(released_raw),
        "data_quality":         node_text(elem, "data_quality"),
        "notes":                node_text(elem, "notes"),
        "master_id":            master_id_val,
        "is_main_release":      is_main,
        "artist_names":         join_pipe(a_names),
        "artist_ids":           join_pipe(a_ids),
        "artist_anvs":          join_pipe(a_anvs),
        "artist_joins":         join_pipe(a_joins),
        "artist_roles":         join_pipe(a_roles),
        "artist_count":         str(len([n for n in a_names if n])),
        "extraartist_names":    join_pipe(ea_names),
        "extraartist_ids":      join_pipe(ea_ids),
        "extraartist_roles":    join_pipe(ea_roles),
        "extraartist_count":    str(len([n for n in ea_names if n])),
        "label_names":          join_unique_pipe(l_names),
        "label_ids":            join_unique_pipe(l_ids),
        "label_catnos":         join_pipe(l_catnos),
        "label_count":          str(len([n for n in l_names if n])),
        "format_names":         join_pipe(f_names),
        "format_qtys":          join_pipe(f_qtys),
        "format_descriptions":  join_pipe(f_descs),
        "format_texts":         join_pipe(f_texts),
        "format_count":         str(len(f_names)),
        "genres":               join_unique_pipe(genres),
        "styles":               join_unique_pipe(styles),
        "track_count":          str(len(t_titles)),
        "track_positions":      join_pipe(t_positions),
        "track_titles":         join_pipe(t_titles),
        "track_durations":      join_pipe(t_durations),
        "image_count":          str(image_count),
        "barcode":              barcode,
        "identifier_types":     join_pipe(id_types),
        "identifier_values":    join_pipe(id_values),
        "video_count":          str(video_count),
        "has_videos":           "1" if video_count > 0 else "0",
        "video_srcs":           join_pipe(v_srcs),
        "company_names":        join_pipe(co_names),
        "company_ids":          join_pipe(co_ids),
        "company_roles":        join_pipe(co_roles),
    }


# ── progress bar ─────────────────────────────────────────────────────────────

def render_progress(
    count: int,
    scanned: int,
    processed_bytes: int,
    total_bytes: int,
    started_at: float,
    limit: int,
) -> str:
    elapsed = max(time.time() - started_at, 1e-6)
    rate = scanned / elapsed
    if limit > 0:
        pct = min(100.0, (count / limit) * 100.0)
    elif total_bytes > 0:
        pct = min(100.0, (processed_bytes / total_bytes) * 100.0)
    else:
        pct = 0.0
    eta_s = max(0.0, (100.0 - pct) / pct * elapsed) if pct > 0.1 else 0.0
    h, rem = divmod(int(eta_s), 3600)
    m, s = divmod(rem, 60)
    eta_str = f"{h}h{m:02d}m" if h else (f"{m}m{s:02d}s" if m else f"{s}s")
    bar_len = 26
    filled = int((pct / 100.0) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    line = f"\r[xml→csv] {bar} {pct:5.1f}%  scanned {scanned:,}"
    if count != scanned:
        line += f"  written {count:,}"
    line += f"  {rate:,.0f} rows/s  ETA {eta_str}"
    return line


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Discogs releases XML dump (.xml.gz) to CSV."
    )
    parser.add_argument("--input", required=True, help="Path to releases .xml.gz dump")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after N release rows (0 = no cap). Use for quick smoke tests.",
    )
    parser.add_argument(
        "--genre",
        default="",
        help='Keep only releases whose genre list contains this value exactly '
             '(e.g. "Electronic"). Default: "" = no filter.',
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable real-time progress bar.",
    )
    args = parser.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    writer = None
    count = 0      # rows written
    scanned = 0    # elements seen (including skipped)
    started_at = time.time()
    last_draw = 0.0
    genre_filter = args.genre.strip()
    total_bytes = in_path.stat().st_size

    if genre_filter:
        print(f"Genre filter active: only '{genre_filter}' releases will be written.")

    use_tqdm = not args.no_progress and _HAS_TQDM
    pbar = None
    prev_bytes = 0

    if use_tqdm:
        pbar = _tqdm(
            total=total_bytes,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc="xml→csv",
            dynamic_ncols=True,
            colour="cyan",
            file=sys.stderr,
        )

    with out_path.open("w", newline="", encoding="utf-8") as out_file:
        for elem, processed_bytes, _ in iter_release_elements(in_path):
            scanned += 1

            # Early genre filter — check XML element before full parse
            if genre_filter and not release_has_genre(elem, genre_filter):
                elem.clear()
                if pbar is not None:
                    delta = processed_bytes - prev_bytes
                    if delta > 0:
                        pbar.update(delta)
                        prev_bytes = processed_bytes
                continue

            row = parse_release(elem)
            if writer is None:
                writer = csv.DictWriter(out_file, fieldnames=RELEASE_FIELDS)
                writer.writeheader()
            writer.writerow(row)
            count += 1
            elem.clear()

            if pbar is not None:
                delta = processed_bytes - prev_bytes
                if delta > 0:
                    pbar.update(delta)
                    prev_bytes = processed_bytes
                now = time.time()
                if now - last_draw >= 0.5:
                    if genre_filter:
                        pbar.set_postfix(scanned=f"{scanned:,}", written=f"{count:,}", refresh=False)
                    else:
                        pbar.set_postfix(rows=f"{count:,}", refresh=False)
                    last_draw = now
            elif not args.no_progress:
                now = time.time()
                if now - last_draw >= 0.2:
                    print(
                        render_progress(
                            count=count,
                            scanned=scanned,
                            processed_bytes=processed_bytes,
                            total_bytes=total_bytes,
                            started_at=started_at,
                            limit=args.limit,
                        ),
                        end="",
                        flush=True,
                        file=sys.stderr,
                    )
                    last_draw = now

            if args.limit and count >= args.limit:
                break

    if pbar is not None:
        # Advance to 100% in case skipped rows left the bar short
        remaining = total_bytes - prev_bytes
        if remaining > 0:
            pbar.update(remaining)
        if genre_filter:
            pbar.set_postfix(scanned=f"{scanned:,}", written=f"{count:,}")
        else:
            pbar.set_postfix(rows=f"{count:,}")
        pbar.close()
    elif not args.no_progress:
        print(
            render_progress(
                count=count,
                scanned=scanned,
                processed_bytes=total_bytes,
                total_bytes=total_bytes,
                started_at=started_at,
                limit=args.limit,
            ),
            end="",
            flush=True,
            file=sys.stderr,
        )
        print(file=sys.stderr)

    elapsed = time.time() - started_at
    if genre_filter:
        print(f"Done. {count:,} '{genre_filter}' rows written "
              f"({scanned:,} scanned, {scanned - count:,} skipped) "
              f"→ {out_path}  ({elapsed:.0f}s)")
    else:
        print(f"Done. {count:,} release rows written to {out_path}  ({elapsed:.0f}s)")


if __name__ == "__main__":
    main()
