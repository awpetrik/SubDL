#!/usr/bin/env python3
"""
SubSource Sub Downloader — CLI tool untuk download subtitle Indonesia dari SubSource.net.
Dirancang untuk Jellyfin: nama subtitle PERSIS sama dengan base filename video (beda ekstensi saja).

Contoh: Movie.2025.mkv → Movie.2025.srt
"""

__version__ = "1.0.0"

import argparse
import difflib
import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import requests  # type: ignore[import-untyped]
from rich.console import Console  # type: ignore[import-untyped]
from rich.table import Table  # type: ignore[import-untyped]

console = Console()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants — Diverifikasi dari .NET wrapper resmi:
# https://github.com/moviecollection/sub-source
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_BASE_URL = "https://api.subsource.net"  # Ref: SubSourceOptions.cs → ApiAddress default
API_SEARCH_PATH = "/api/v1/movies/search"  # Ref: SubSourceService.cs → SearchMoviesAsync
API_SUBTITLES_PATH = "/api/v1/subtitles"   # Ref: SubSourceService.cs → GetSubtitlesAsync
API_SUBTITLE_DETAIL_PATH = "/api/v1/subtitles/{subtitle_id}"   # Ref: SubSourceService.cs → GetSubtitleByIdAsync
API_DOWNLOAD_PATH = "/api/v1/subtitles/{subtitle_id}/download"  # Ref: SubSourceService.cs → DownloadSubtitleAsync
API_AUTH_HEADER = "X-API-Key"  # Ref: SubSourceService.cs → SendRequestAsync → request.Headers.Add("X-API-Key", ...)

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v"}

# Tags to strip from filenames (case-insensitive, whole-word)
STRIP_TAGS = [
    "1080p", "720p", "2160p", "4K", "480p",
    "WEB-DL", "WEBRip", "BluRay", "Blu-Ray", "HDTV",
    "x264", "x265", "HEVC", "AVC", "H264", "H265",
    "AAC", "DTS", "AC3", "DD5.1", "FLAC", "MP3",
    "HDR", "HDR10", "SDR", "REMUX",
    "EXTENDED", "UNRATED", "REMASTERED", "PROPER", "REPACK",
    "NF", "AMZN", "HULU", "DSNP", "ATVP", "MAX",
]

# Language strings for Indonesian (case-insensitive matching)
INDONESIAN_LANG_STRINGS = {"indonesian", "indonesia", "id", "bahasa indonesia", "ind"}

# Config file for storing API key
CONFIG_DIR = Path.home() / ".subdl"
CONFIG_FILE = CONFIG_DIR / "config"


def _load_api_key() -> str:
    """Load API key dari environment variable atau config file.

    Prioritas:
    1. Environment variable SUBSOURCE_API_KEY
    2. Config file ~/.subdl/config
    """
    # Cek env var dulu
    env_key = os.environ.get("SUBSOURCE_API_KEY", "").strip()
    if env_key:
        return env_key

    # Cek config file
    if CONFIG_FILE.exists():
        try:
            content = CONFIG_FILE.read_text(encoding="utf-8").strip()
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("api_key="):
                    key = line[len("api_key="):].strip()  # type: ignore[index]
                    if key:
                        return key
        except OSError:
            pass

    return ""


def _save_api_key(api_key: str) -> bool:
    """Simpan API key ke config file ~/.subdl/config."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(f"api_key={api_key}\n", encoding="utf-8")
        # Set permission 600 (owner read/write only) untuk keamanan
        try:
            CONFIG_FILE.chmod(0o600)
        except OSError:
            pass  # Windows might not support chmod
        return True
    except OSError as e:
        print(f"  ⚠  Tidak bisa simpan config: {e}")
        return False


def _prompt_api_key() -> str:
    """Prompt user untuk memasukkan API key secara interaktif."""
    print()
    print("🔑 API Key belum dikonfigurasi.")
    print()
    print("Cara mendapatkan API key:")
    print("  1. Buka https://subsource.net")
    print("  2. Login atau buat akun")
    print("  3. Klik Profile → API Key")
    print("  4. Copy API key yang ditampilkan")
    print()

    try:
        api_key = input("Paste API key di sini: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n⚠  Dibatalkan.")
        sys.exit(0)

    if not api_key:
        print("❌ API key tidak boleh kosong.")
        sys.exit(1)

    # Simpan ke config
    if _save_api_key(api_key):
        print(f"✅ API key tersimpan di: {CONFIG_FILE}")
        print("   Tidak perlu input ulang di lain waktu.")
    print()

    return api_key


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SubSourceClient
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SubSourceClient:
    """Client untuk SubSource API.

    Semua endpoint diverifikasi dari source code .NET wrapper resmi:
    https://github.com/moviecollection/sub-source/blob/main/Source/MovieCollection.SubSource/SubSourceService.cs
    """

    def __init__(self, api_key: str, timeout: int = 20):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            API_AUTH_HEADER: self.api_key,
            "Accept": "application/json",
            "User-Agent": f"SubDL-CLI/{__version__}",
        })

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None,
                 stream: bool = False, expect_json: bool = True) -> requests.Response:
        """Kirim request ke API dengan retry logic dan error handling.

        Retry: 2x untuk timeout/connection, 3x untuk 429 rate limit.
        Backoff: 0.5s, 1.5s untuk timeout/connection; Retry-After header untuk 429.
        """
        url = API_BASE_URL + path
        last_exc: Optional[BaseException] = None

        for attempt in range(3):  # Max 3 attempts
            try:
                resp = self.session.request(
                    method, url, params=params, timeout=self.timeout, stream=stream
                )

                if resp.status_code in (401, 403):
                    print(f"❌ API key invalid atau expired. Set env var: export SUBSOURCE_API_KEY=your_key")
                    return resp

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    if attempt < 2:
                        print(f"⏳ Rate limited. Tunggu {retry_after}s...")
                        time.sleep(retry_after)
                        continue
                    else:
                        print(f"❌ Rate limit exceeded setelah 3 percobaan.")
                        return resp

                if 500 <= resp.status_code < 600:
                    if attempt < 2:
                        backoff = [1, 3][attempt]
                        print(f"🔄 Server error ({resp.status_code}). Retry {attempt + 1}/3...")
                        time.sleep(backoff)
                        continue
                    else:
                        print(f"❌ Server error ({resp.status_code}) setelah retry.")
                        return resp

                return resp

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exc = e
                if attempt < 2:
                    backoff = [0.5, 1.5][attempt]
                    print(f"🔄 Timeout/Koneksi gagal. Retry {attempt + 1}/3...")
                    time.sleep(backoff)
                else:
                    print(f"❌ Gagal koneksi ke SubSource setelah 3 percobaan.")
                    
        # Return fallback pseudo-response (not strictly typed but caught upstream)
        err_resp = requests.Response()
        err_resp.status_code = 503
        return err_resp

    def search_titles(self, query: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search film/series di SubSource.

        Ref: SubSourceService.cs → SearchMoviesAsync
        Endpoint: GET /api/v1/movies/search?searchType=text&q=<query>[&year=<year>]
        Response: { "data": [ { "movieId", "title", "type", "releaseYear", ... }, ... ] }
        """
        params: Dict[str, Any] = {
            "searchType": "text",
            "q": query,
        }
        if year is not None:
            params["year"] = year

        resp = self._request("GET", API_SEARCH_PATH, params=params)

        if resp.status_code in (401, 403):
            return []

        if not resp.ok:
            print(f"⚠  HTTP {resp.status_code}: {resp.text[0:200]}")  # type: ignore[index]
            return []

        try:
            data = resp.json()
        except json.JSONDecodeError:
            self._save_debug_response(resp.text)
            return []

        # Response wrapper: { "data": [...] } atau langsung list
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return cast(List[Dict[str, Any]], data.get("data") or data.get("items") or [])
        return []

    def list_subtitles(self, content_id: int, language: str = "indonesian") -> List[Dict[str, Any]]:
        """Ambil daftar subtitle untuk content tertentu.

        Ref: SubSourceService.cs → GetSubtitlesAsync
        Endpoint: GET /api/v1/subtitles?movieId=<id>&language=<lang>
        Response: { "data": [ { "subtitleId", "language", "releaseInfo", ... }, ... ] }
        """
        params: Dict[str, Any] = {
            "movieId": content_id,
            "language": language,
        }

        resp = self._request("GET", API_SUBTITLES_PATH, params=params)

        if resp.status_code in (401, 403):
            return []

        if not resp.ok:
            print(f"⚠  HTTP {resp.status_code}: {resp.text[0:200]}")  # type: ignore[index]
            return []

        try:
            data = resp.json()
        except json.JSONDecodeError:
            self._save_debug_response(resp.text)
            return []

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return cast(List[Dict[str, Any]], data.get("data") or data.get("items") or [])
        return []

    def download_subtitle(self, sub_id: int) -> Optional[bytes]:
        """Download subtitle file (bisa ZIP atau SRT langsung).

        Ref: SubSourceService.cs → DownloadSubtitleAsync
        Endpoint: GET /api/v1/subtitles/{id}/download
        Response: binary file (ZIP archive atau SRT langsung)
        """
        path = API_DOWNLOAD_PATH.format(subtitle_id=sub_id)

        try:
            resp = self._request("GET", path, stream=True, expect_json=False)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"❌ Download gagal: {e}")
            return None

        if resp.status_code in (401, 403):
            return None

        if not resp.ok:
            print(f"❌ Download gagal: HTTP {resp.status_code}")
            return None

        return resp.content

    def _save_debug_response(self, raw_text: str):
        """Simpan raw response ke file debug untuk troubleshooting."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = Path.cwd() / f".subdl_debug_{timestamp}.json"
        try:
            debug_file.write_text(raw_text, encoding="utf-8")
            print(f"⚠  Response API tidak sesuai ekspektasi.")
            print(f"📝 Raw response disimpan ke {debug_file.name}")
        except OSError:
            print(f"⚠  Response API tidak sesuai ekspektasi (tidak bisa simpan debug file).")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def extract_episode_tag(filename: str) -> Optional[str]:
    """Ekstrak tag episode (misal S01E01, 1x01, E01) dari teks."""
    match = re.search(r'\b(S\d{1,2}E\d{1,2}|E\d{1,2}|\d{1,2}x\d{2,3})\b', filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def parse_title_year(filename: str) -> tuple[str, Optional[int]]:
    """Parse judul dan tahun dari filename video.

    Args:
        filename: nama file video (dengan ekstensi)

    Returns:
        (cleaned_title: str, year: Optional[int])

    Logika:
    1. Hapus ekstensi
    2. Deteksi tahun (19xx/20xx) — ambil yang pertama
    3. Hapus tags umum (resolusi, codec, source, dll)
    4. Hapus group tags dalam [] atau () yang bukan tahun
    5. Bersihkan separator → spasi
    6. Deteksi pola series (S01E01 atau 1x01) dan sertakan
    """
    # Remove extension
    stem = Path(filename).stem

    # Detect series pattern before cleaning
    series_match = re.search(r'(S\d{1,2}E\d{1,2})', stem, re.IGNORECASE)
    if not series_match:
        series_match = re.search(r'(\d{1,2}x\d{2,3})', stem, re.IGNORECASE)
    
    series_tag = None
    if series_match:
        series_tag = series_match.group(1)
        # Untuk TV series, buang semua string setelah tag episode (cth: .Rookies.REPACK.1080p)
        stem = stem[:series_match.start()]  # type: ignore[index]

    # Detect year — ambil yang PERTAMA ditemukan
    year_match = re.search(r'\b((?:19|20)\d{2})\b', stem)
    year = int(year_match.group(1)) if year_match else None

    # Remove content in brackets/parentheses UNLESS it's the year
    def _remove_brackets(text: str) -> str:
        # Remove [...] contents
        text = re.sub(r'\[([^\]]*)\]', lambda m: m.group(0) if (year and str(year) in m.group(1)) else '', text)
        # Remove (...) contents unless it's just the year
        text = re.sub(r'\(([^\)]*)\)', lambda m: m.group(0) if (year and m.group(1).strip() == str(year)) else '', text)
        return text

    cleaned = _remove_brackets(stem)

    # Remove known tags (case-insensitive, whole words)
    for tag in STRIP_TAGS:
        # Escape special regex chars in tag
        escaped = re.escape(tag)
        cleaned = re.sub(r'(?<![a-zA-Z0-9])' + escaped + r'(?![a-zA-Z0-9])', '', cleaned, flags=re.IGNORECASE)

    # Remove series tag from title (we'll add it back to query if needed)
    if series_tag:
        cleaned = re.sub(re.escape(series_tag), '', cleaned, flags=re.IGNORECASE)

    # Remove year from the cleaned title
    if year:
        cleaned = re.sub(r'\b' + str(year) + r'\b', '', cleaned)

    # Replace separators with spaces
    cleaned = re.sub(r'[._\-]+', ' ', cleaned)

    # Remove leftover parentheses/brackets
    cleaned = re.sub(r'[(){}\[\]]', '', cleaned)

    # Collapse multiple spaces and strip
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return (cleaned, year)


def choose_from_list(items: List[str], prompt: str, default_index: int = 0,
                     non_interactive: bool = False) -> Optional[int]:
    """Tampilkan list pilihan dan minta user pilih.

    Returns:
        Index yang dipilih (0-based), atau None kalau user skip.
    """
    if not items:
        return None

    if non_interactive:
        return default_index

    print(prompt)
    for i, item in enumerate(items):
        print(f"  {item}")
    print()

    max_retries = 3
    for _ in range(max_retries):
        try:
            choice = input(f"Pilih [1-{len(items)}] (default {default_index + 1}, 's' untuk skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        if choice == "":
            return default_index

        if choice.lower() in ("s", "skip"):
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return idx
            else:
                print(f"  ⚠  Input di luar range 1-{len(items)}. Coba lagi.")
        except ValueError:
            print(f"  ⚠  Input tidak valid. Masukkan angka 1-{len(items)}, atau 's' untuk skip.")

    print("  ⏭  Terlalu banyak percobaan, skip.")
    return None


def is_indonesian(lang_string: str) -> bool:
    """Cek apakah string bahasa menunjukkan Indonesia.

    Menggunakan substring match case-insensitive terhadap daftar yang diketahui:
    "indonesian", "indonesia", "id", "bahasa indonesia", "ind"
    """
    if not lang_string:
        return False
    lower = lang_string.lower().strip()
    for indo_str in INDONESIAN_LANG_STRINGS:
        if indo_str in lower or lower in indo_str:
            return True
    return False


def is_srt(sub_item: Dict[str, Any]) -> bool:
    """Cek apakah subtitle item berformat SRT.

    Cek field: format, extension, type, releaseType, productionType.
    EXCLUDE: ass, ssa, vtt, sub, idx.
    SubSource API mungkin tidak selalu menyediakan field format secara eksplisit,
    jadi kalau tidak ada field terkait, kita anggap SRT (karena mayoritas SubSource = SRT).
    """
    excluded_formats = {"ass", "ssa", "vtt", "sub", "idx"}

    # Cek berbagai kemungkinan field yang menunjukkan format
    for key in ("format", "extension", "type", "fileType"):
        val = sub_item.get(key)
        if val and isinstance(val, str):
            val_lower = val.lower().strip()
            if val_lower in excluded_formats:
                return False
            if "srt" in val_lower:
                return True

    # Cek releaseInfo (list of strings) untuk petunjuk format
    release_info = sub_item.get("releaseInfo", [])
    if isinstance(release_info, list):
        for info in release_info:
            if isinstance(info, str):
                info_lower = info.lower()
                if any(fmt in info_lower for fmt in excluded_formats):
                    return False

    # Kalau tidak ada indikasi format, anggap SRT (default di SubSource)
    return True


def extract_srt_from_zip(zip_bytes: bytes, video_stem: str) -> Optional[bytes]:
    """Extract file SRT terbaik dari ZIP archive.

    Args:
        zip_bytes: raw bytes dari file ZIP
        video_stem: basename video tanpa ekstensi, untuk similarity matching

    Returns:
        bytes konten SRT, atau None kalau tidak ada file .srt dalam ZIP
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        print("  ⚠  File ZIP corrupt atau bukan ZIP valid.")
        return None

    srt_files = [name for name in zf.namelist()
                 if name.lower().endswith(".srt") and not name.startswith("__MACOSX")]

    if not srt_files:
        return None

    if len(srt_files) == 1:
        return zf.read(srt_files[0])

    # Multiple SRT files → pilih yang paling mirip nama dengan video
    video_ep = extract_episode_tag(video_stem)

    def _score_extracted_srt(srt_name: str) -> float:
        srt_stem = Path(srt_name).stem
        score = 0.0
        if video_ep:
            srt_ep = extract_episode_tag(srt_stem)
            if srt_ep and video_ep == srt_ep:
                score = score + 50.0
            elif srt_ep and video_ep != srt_ep:
                score = score - 50.0
        
        sim = difflib.SequenceMatcher(None, video_stem.lower(), srt_stem.lower()).ratio()
        return score + sim

    srt_files.sort(key=_score_extracted_srt, reverse=True)
    return zf.read(srt_files[0])


def save_srt_atomic(target_path: Path, data: bytes) -> bool:
    """Simpan file SRT secara atomic (tulis ke temp dulu, lalu rename).

    Args:
        target_path: path tujuan file .srt
        data: raw bytes konten SRT

    Returns:
        True kalau sukses, False kalau gagal
    """
    tmp_path = target_path.with_suffix(".srt.tmp")
    try:
        tmp_path.write_bytes(data)
        # atomic rename on POSIX systems
        tmp_path.replace(target_path)
        return True
    except PermissionError:
        print(f"  ❌ Tidak bisa tulis ke {target_path}: permission denied. (Coba check ownership folder)")
        _cleanup_tmp(tmp_path)
        return False
    except OSError as e:
        print(f"  ❌ Error menulis file: {e}")
        _cleanup_tmp(tmp_path)
        return False


def _cleanup_tmp(tmp_path: Path):
    """Hapus temp file kalau ada."""
    try:
        if tmp_path.exists():
            tmp_path.unlink()
    except OSError:
        pass


def _format_movie_choice(idx: int, movie: Dict[str, Any]) -> str:
    """Format 1 item movie untuk ditampilkan di list pilihan."""
    title = movie.get("title", "Unknown")
    year = movie.get("releaseYear", "?")
    mtype = movie.get("type", "?")
    return f"[{idx + 1}] {title} ({year}) — {mtype}"


def _print_subtitle_table(subs: List[Dict[str, Any]], header: str) -> None:
    """Print daftar subtitle dalam rich table yang rapi."""
    print(header)

    table = Table(show_header=True, header_style="bold cyan", box=None,
                  pad_edge=False, padding=(0, 1))
    table.add_column("#", style="bold", width=3, justify="right")
    table.add_column("Release", style="white", min_width=20, max_width=50, no_wrap=False)
    table.add_column("Rating", style="yellow", width=7, justify="center")
    table.add_column("HI", width=4, justify="center")
    table.add_column("DL", style="dim", width=6, justify="right")

    for i, sub in enumerate(subs):
        # Release info
        release: Any = sub.get("releaseInfo", [])
        if isinstance(release, list):
            release_str = ", ".join(str(r) for r in list(release)[0:3])  # type: ignore[index]
        else:
            release_str = str(release)[0:80]  # type: ignore[index]
        if not release_str:
            release_str = "N/A"

        # Rating
        rating_str = "-"
        rating = sub.get("rating")
        if rating and isinstance(rating, dict):
            good = rating.get("good", 0)
            total = rating.get("total", 0)
            if total > 0:
                rating_str = f"{good}/{total}"

        # HI
        hi = sub.get("hearingImpaired")
        hi_str = "Yes" if hi else "No" if hi is not None else "-"

        # Downloads
        downloads = sub.get("downloads")
        dl_str = str(downloads) if downloads is not None else "-"

        table.add_row(str(i + 1), release_str, rating_str, hi_str, dl_str)

    console.print(table)
    print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Core Processing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def process_video(video_path: Path, client: SubSourceClient, args: argparse.Namespace,
                  index: int = 1, total: int = 1,
                  title_cache: Optional[Dict[str, Dict[str, Any]]] = None,
                  subtitle_cache: Optional[Dict[int, List[Dict[str, Any]]]] = None,
                  conflict_action: Optional[List[str]] = None) -> str:
    """Proses 1 file video: search → pilih → list subtitles → download → save.

    Returns: "success" | "skip" | "fail"
    """
    filename = video_path.name
    target_srt = video_path.with_suffix(".srt")

    print(f"\n📂 [{index}/{total}] {filename}")

    # --- Cek subtitle existing ---
    if target_srt.exists() and not args.force:
        if conflict_action and conflict_action[0] == "replace_all":
            pass  # Force replace
        elif conflict_action and conflict_action[0] == "skip_all":
            print("  ⏭  Skip (Skip All aktif).")
            return "skip"
        else:
            try:
                answer = input(f"⚠  Subtitle sudah ada untuk {filename}.\n   [y] Replace, [n] Skip, [a] Replace All, [s] Skip All: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            
            if answer == "a":
                if conflict_action is not None:
                    conflict_action[0] = "replace_all"
            elif answer == "s":
                if conflict_action is not None:
                    conflict_action[0] = "skip_all"
                print("  ⏭  Skip.")
                return "skip"
            elif answer != "y":
                print("  ⏭  Skip.")
                return "skip"

    # --- Parse judul & tahun ---
    title, year = parse_title_year(filename)
    if not title:
        print(f"  ❌ Tidak bisa parse judul dari '{filename}'.")
        return "fail"

    year_str = f" ({year})" if year else ""
    print(f"🔍 Mencari: \"{title}\"{year_str}...")

    if args.dry_run:
        print(f"  🔸 [DRY RUN] Akan search: \"{title}\"{year_str}")
        print(f"  🔸 [DRY RUN] Target: {target_srt}")
        return "success"

    if title_cache is None:
        title_cache = {}
    cache_key = f"{title}_{year}"

    if cache_key in title_cache:
        chosen_movie = title_cache[cache_key]
        print(f"  ⚡ Memakai judul dari cache: {chosen_movie.get('title')} ({chosen_movie.get('releaseYear')})")
    else:
        # --- Search API ---
        try:
            results = client.search_titles(title, year)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"  ❌ Network error saat search: {e}")
            return "fail"

        if args.verbose and results:
            print(f"  🔧 [VERBOSE] Search response: {json.dumps(results, default=str)[0:500]}")  # type: ignore[index]

        if not results:
            print(f"  ❌ Tidak ada hasil untuk \"{title}\".")
            return "fail"

        # --- Pilih judul ---
        display_results: List[Dict[str, Any]] = list(results)[0:10]  # type: ignore[index]
        choices = [_format_movie_choice(i, m) for i, m in enumerate(display_results)]
        prompt = f"Hasil pencarian untuk \"{title}\":"

        chosen_idx = choose_from_list(choices, prompt, default_index=0,
                                      non_interactive=args.non_interactive)

        if chosen_idx is None:
            print("  ⏭  Skip.")
            return "skip"

        chosen_movie = display_results[chosen_idx]
        title_cache[cache_key] = chosen_movie

    movie_title = chosen_movie.get("title", "?")
    movie_year = chosen_movie.get("releaseYear", "?")
    movie_type = chosen_movie.get("type", "?")
    content_id = chosen_movie.get("movieId")

    if content_id is None:
        print(f"  ❌ Movie ID tidak ditemukan dalam response.")
        return "fail"

    print(f"📋 Memilih judul: {movie_title} ({movie_year}) — {movie_type}")

    # --- List subtitles ---
    if subtitle_cache is None:
        subtitle_cache = {}

    if content_id in subtitle_cache:
        subtitles = subtitle_cache[content_id]
        print(f"📑 Menggunakan daftar subtitle dari cache...")
    else:
        print(f"📑 Mengambil daftar subtitle...")
        try:
            subtitles = client.list_subtitles(content_id, language="indonesian")
            subtitle_cache[content_id] = subtitles
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"  ❌ Network error saat list subtitles: {e}")
            return "fail"

    if args.verbose and subtitles:
        print(f"  🔧 [VERBOSE] Subtitles response: {json.dumps(subtitles, default=str)[0:500]}")  # type: ignore[index]

    # --- Filter: Indonesian + SRT ---
    filtered: List[Dict[str, Any]] = []
    for sub in subtitles:
        lang = sub.get("language", "")
        if is_indonesian(lang) and is_srt(sub):
            filtered.append(sub)

    if not filtered:
        print(f"  ❌ Tidak ada subtitle Indonesia format SRT.")
        return "fail"

    # --- Auto-Matching & Scoring ---
    video_ep = extract_episode_tag(filename)
    video_lower = filename.lower()

    def _score_subtitle(sub: Dict[str, Any]) -> float:
        rel_info = sub.get("releaseInfo", [])
        rel_str = str(rel_info[0]) if isinstance(rel_info, list) and rel_info else str(rel_info)
        rel_lower = rel_str.lower()
        
        ep_score: float = 0.0
        # 1. Episode Match (+50/-50)
        if video_ep:
            sub_ep = extract_episode_tag(rel_str)
            if sub_ep and video_ep == sub_ep:
                ep_score = 50.0
            elif sub_ep and video_ep != sub_ep:
                # Penalty explicitly mismatched episode
                ep_score = -50.0

        qual_score: float = 0.0
        # 2. Quality Match (+10)
        qualities = ["web-dl", "webdl", "WEBDL", "WEB", "bluray", "hdrip", "hdtv", "webrb", "webrip", "1080p", "720p", "2160p"]
        for q in qualities:
            if q in video_lower and q in rel_lower:
                qual_score = 10.0
                break

        codec_score: float = 0.0
        # 3. Codec Match (+10)
        codecs = ["x265", "hevc", "x264", "avc"]
        for c in codecs:
            if c in video_lower and c in rel_lower:
                codec_score = 10.0
                break
                
        # 4. Penalty HI (-15)
        hi_penalty: float = -15.0 if sub.get("hearingImpaired") else 0.0
            
        # Tie-breaker: difflib similarity (0 to 1)
        sim: float = float(difflib.SequenceMatcher(None, video_lower, rel_lower).ratio())
        
        # Save score for display/debugging
        final_score: float = ep_score + qual_score + codec_score + hi_penalty + sim
        sub["_score"] = final_score
        return final_score

    filtered.sort(key=_score_subtitle, reverse=True)

    # --- Pilih subtitle ---
    display_subs: List[Dict[str, Any]] = list(filtered)[0:20]  # type: ignore[index]
    sub_prompt = f"Subtitle tersedia ({len(filtered)} total):"

    sub_idx = None
    best_sub = display_subs[0] if display_subs else None

    # Auto-match threshold check
    if best_sub and best_sub.get("_score", 0) >= 50:
        if not args.non_interactive:
            print(f"  ✨ Auto-match! Skor {best_sub.get('_score', 0):.2f} (Episode {video_ep})")
        sub_idx = 0
    else:
        if args.non_interactive:
            sub_idx = 0
        else:
            _print_subtitle_table(display_subs, sub_prompt)
            max_retries = 3
            for _ in range(max_retries):
                try:
                    choice = input(f"Pilih [1-{len(display_subs)}] (default 1, 's' untuk skip): ").strip()
                except (EOFError, KeyboardInterrupt):
                    sub_idx = None
                    break
                if choice == "":
                    sub_idx = 0
                    break
                if choice.lower() in ("s", "skip"):
                    sub_idx = None
                    break
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(display_subs):
                        sub_idx = idx
                        break
                    else:
                        print(f"  ⚠  Input di luar range 1-{len(display_subs)}. Coba lagi.")
                except ValueError:
                    print(f"  ⚠  Input tidak valid. Masukkan angka 1-{len(display_subs)}, atau 's' untuk skip.")
            else:
                print("  ⏭  Terlalu banyak percobaan, skip.")
                sub_idx = None

    if sub_idx is None:
        print("  ⏭  Skip.")
        return "skip"

    chosen_sub = display_subs[sub_idx]
    sub_id = chosen_sub.get("subtitleId")

    if sub_id is None:
        print(f"  ❌ Subtitle ID tidak ditemukan dalam response.")
        return "fail"

    print(f"⬇  Mengunduh subtitle #{sub_id}...")

    # --- Download subtitle ---
    try:
        raw_data = client.download_subtitle(sub_id)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        print(f"  ❌ Network error saat download: {e}")
        return "fail"

    if raw_data is None:
        print(f"  ❌ Download subtitle gagal.")
        return "fail"

    if not raw_data:
        print(f"  ❌ Download mengembalikan data kosong.")
        return "fail"

    # --- Detect ZIP vs SRT using magic bytes ---
    srt_data: Optional[bytes] = None
    if bytes(raw_data[0:4]) == b'PK\x03\x04':  # type: ignore[index]
        # It's a ZIP file
        srt_data = extract_srt_from_zip(raw_data, video_path.stem)
        if srt_data is None:
            print(f"  ❌ Tidak ada file .srt dalam ZIP yang didownload.")
            return "fail"
    else:
        # Assume it's raw SRT content
        srt_data = raw_data

    # --- Save atomic ---
    if save_srt_atomic(target_srt, srt_data):
        print(f"✅ Tersimpan: {target_srt}")
        return "success"
    else:
        return "fail"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# File Discovery
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def discover_video_files(path: Path) -> List[Path]:
    """Temukan file video dari path (file tunggal atau folder recursive).

    Returns:
        List of Path, sorted alphabetically
    """
    def _is_valid_video(p: Path) -> bool:
        name = p.name
        # Skip hidden files and macOS AppleDouble metadata files
        if name.startswith("."):
            return False
        # Optional: skip sample, extras, trailer
        lower_name = name.lower()
        if "sample" in lower_name or "extras" in lower_name or "trailer" in lower_name:
            return False
        return True

    if path.is_file():
        if path.suffix.lower() in VIDEO_EXTENSIONS and _is_valid_video(path):
            return [path]
        else:
            print(f"⚠  '{path.name}' bukan file video yang didukung, atau di-skip.")
            print(f"   Ekstensi yang didukung: {', '.join(sorted(VIDEO_EXTENSIONS))}")
            return []

    if path.is_dir():
        videos = []
        for ext in VIDEO_EXTENSIONS:
            videos.extend(path.rglob(f"*{ext}"))
            # Also handle uppercase extensions
            videos.extend(path.rglob(f"*{ext.upper()}"))

        # Deduplicate (in case of case-insensitive filesystem) and filter
        seen = set()
        unique_videos = []
        for v in videos:
            resolved = v.resolve()
            if resolved not in seen:
                seen.add(resolved)
                if _is_valid_video(v):
                    unique_videos.append(v)

        # Sort alphabetically
        unique_videos.sort(key=lambda p: str(p).lower())
        return unique_videos

    return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Entry Point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_parser() -> argparse.ArgumentParser:
    """Build argparse parser."""
    parser = argparse.ArgumentParser(
        prog="subdl",
        description="SubSource Sub Downloader — Download subtitle Indonesia dari SubSource.net untuk Jellyfin.",
        epilog="Contoh: python3 subdl.py /path/to/movie.mkv --force",
    )
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        default=None,
        help="Path ke file video atau folder yang berisi file video.",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="id",
        help="Kode bahasa (default: id). Saat ini hanya 'id' yang diimplementasi penuh.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        dest="non_interactive",
        help="Auto-pilih kandidat judul pertama dan subtitle pertama dari list.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite subtitle tanpa prompt.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print rencana tindakan tanpa eksekusi.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print raw API response untuk debugging (truncated ke 500 char).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _clean_dragged_path(raw: str) -> str:
    r"""Bersihkan path hasil drag-and-drop dari terminal.

    macOS Terminal menambahkan backslash escape untuk banyak karakter:
      /Users/name/My\ Movies\ \(2024\)/file.mkv
    Linux terminal biasanya menambahkan quotes.
    """
    cleaned = raw.strip()
    # Remove surrounding quotes (single or double)
    if (cleaned.startswith('"') and cleaned.endswith('"')) or \
       (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1]  # type: ignore[index]
    # Remove ALL backslash escapes: \( → (, \ → space, \' → ', etc.
    # This handles macOS Terminal escaping for spaces, parens, brackets, etc.
    cleaned = re.sub(r'\\(.)', r'\1', cleaned)
    # Expand ~ to home directory
    cleaned = os.path.expanduser(cleaned)
    return cleaned.strip()


def _run_session(input_path: Path, client: SubSourceClient, args: argparse.Namespace) -> None:
    """Proses satu session: discover video files → process masing-masing → print ringkasan."""
    videos = discover_video_files(input_path)
    if not videos:
        print(f"❌ Tidak ada file video ditemukan di: {input_path}")
        print(f"   Ekstensi yang didukung: {', '.join(sorted(VIDEO_EXTENSIONS))}")
        return

    print(f"🎬 Ditemukan {len(videos)} file video.")
    if args.dry_run:
        print("🔸 Mode DRY RUN aktif — tidak ada file yang akan dimodifikasi.\n")

    stats = {"success": 0, "skip": 0, "fail": 0}
    session_title_cache: Dict[str, Dict[str, Any]] = {}
    session_sub_cache: Dict[int, List[Dict[str, Any]]] = {}
    session_conflict_action: List[str] = ["prompt"]

    for i, video in enumerate(videos, start=1):
        try:
            result = process_video(video, client, args, index=i, total=len(videos), 
                                   title_cache=session_title_cache, subtitle_cache=session_sub_cache,
                                   conflict_action=session_conflict_action)
            stats[result] = stats.get(result, 0) + 1
        except KeyboardInterrupt:
            print("\n\n⚠  Dibatalkan oleh user.")
            break
        except Exception as e:
            print(f"💥 Error tidak terduga untuk {video.name}: {e}")
            stats["fail"] += 1

    # Summary
    print("\n━━━━━━━━━━━━━━━━━━━━━")
    print("📊 Ringkasan:")
    print(f"  ✅ Sukses   : {stats['success']}")
    print(f"  ⏭  Dilewati : {stats['skip']}")
    print(f"  ❌ Gagal    : {stats['fail']}")
    print("━━━━━━━━━━━━━━━━━━━━━")


def main() -> None:
    """Entry point utama CLI."""
    parser = build_parser()
    args = parser.parse_args()

    # --force implies non-interactive for replace prompts
    if args.force:
        pass  # force overrides prompt in process_video directly

    # Validate API key (env var → config file → prompt interaktif)
    api_key = _load_api_key()
    if not api_key:
        api_key = _prompt_api_key()

    client = SubSourceClient(api_key=api_key)

    # ── CLI mode: path given as argument → single run ──
    if args.path is not None:
        input_path = Path(args.path)
        if not input_path.exists():
            print(f"❌ Path tidak ditemukan: {args.path}")
            sys.exit(2)
        _run_session(input_path, client, args)
        return

    # ── Interactive mode: continuous loop ──
    print()
    print("┌─────────────────────────────────────────────┐")
    print("│  🎬 SubSource Sub Downloader by awpetrik    │")
    print("│  Download subtitle Indonesia secara instan  │")
    print("│     https://github.com/awpetrik/SubDL       │")
    print("└─────────────────────────────────────────────┘")
    print()

    first_run = True
    while True:
        if first_run:
            print("📂 Drag & drop file video atau folder, lalu tekan Enter:")
            print("   (ketik 'q' untuk keluar)")
        else:
            print("\n📂 Drag lagi, atau ketik 'q' untuk keluar:")

        print()
        try:
            raw_path = input("   ▸ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Sampai jumpa!")
            break

        if not raw_path:
            print("  ⚠  Tidak ada path. Coba lagi.")
            continue

        if raw_path.lower() in ("q", "quit", "exit"):
            print("\n👋 Sampai jumpa!")
            break

        cleaned = _clean_dragged_path(raw_path)
        input_path = Path(cleaned)

        if not input_path.exists():
            print(f"  ❌ Path tidak ditemukan: {cleaned}")
            print("  Coba drag ulang.")
            continue

        _run_session(input_path, client, args)
        first_run = False


if __name__ == "__main__":
    main()

