# SubSource Sub Downloader (`subdl`)

<p align="center">
<img width="1206" height="860" alt="image" src="https://github.com/user-attachments/assets/e68cabb4-ec28-43f7-af97-1a3aab3afa01" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Requests-066F24?style=for-the-badge&logo=python&logoColor=white" alt="Requests" />
  <img src="https://img.shields.io/badge/Rich-000000?style=for-the-badge&logo=python&logoColor=white" alt="Rich" />
</p>

English | [Bahasa Indonesia](README.md)

CLI tool to download Indonesian subtitles from [SubSource.net](https://subsource.net) 

Subtitle filenames automatically match the video filename EXACTLY (only the extension changes), so Jellyfin auto-recognizes them without extra configuration.

```
Movie.2025.1080p.WEB-DL.mkv  →  Movie.2025.1080p.WEB-DL.srt
```

---

## Quick Install (EXPERIMENTAL)

Run one command — automatically check Python, install dependencies, and run:

**Linux / macOS:** (Tested on Linux)
```bash
curl -sSL https://rivaldi.space/SubDL | bash
```

**Windows (PowerShell):** (Untested, please let me know if it doesn't work or errors)
```powershell
irm https://rivaldi.space/SubDLWin | iex
```

> The script will install SubDL to `~/.subdl/` (Linux/macOS) or `%USERPROFILE%\.subdl\` (Windows) with a virtual environment inside. The installer will also **automatically add `subdl` to your PATH**, allowing you to run it from any terminal.

---

## Manual Install

If you prefer manual installation:

- **Python 3.9+**
- **pip** (Python package manager)

```bash
git clone https://github.com/awpetrik/SubDL.git
cd SubDL
pip install -r requirements.txt
python3 subdl.py
```

Dependencies: only `requests` — no additional dependencies outside the standard library.

---

## API Key

The first time you run SubDL, you will be asked to enter an API key:

```
🔑 API Key not configured.

How to get an API key:
  1. Open https://subsource.net
  2. Login or create an account
  3. Click Profile → API Key
  4. Copy the displayed API key

Paste API key here: ********
✅ API key saved at: ~/.subdl/config
```

The API key is saved automatically — **no need to re-enter it** later.

### Alternative: Environment Variable

```bash
# Linux / macOS
export SUBSOURCE_API_KEY=your_key_here

# Windows CMD
set SUBSOURCE_API_KEY=your_key_here

# PowerShell
$env:SUBSOURCE_API_KEY="your_key_here"
```

> Environment variables always take precedence if set (override config file).

---

## Usage

### Interactive Mode (Drag & Drop)

Just run without arguments:

```bash
python3 subdl.py
```

Then **drag & drop** a video file or folder into the terminal and press Enter:

```
┌─────────────────────────────────────────────┐
│  🎬 SubSource Sub Downloader by awpetrik    │
│  Download Indonesian subtitles instantly    │
│     https://github.com/awpetrik/SubDL       │
└─────────────────────────────────────────────┘

📂 Drag & drop video file or folder here, then press Enter:

    ▸ /media/movies/Inception.2010.mkv
```

> 💡 **Tip:** In most terminals (GNOME Terminal, Konsole, Windows Terminal, iTerm2), simply drag the file from your file manager and drop it into the terminal window — the path will be filled automatically.

### CLI Mode (Direct)

You can also pass the path directly as an argument:

```bash
python3 subdl.py <path> [options]
```

### Flags

| Flag                | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| `--lang LANG`       | Language code, default: `id`. Currently only `id` is fully implemented.    |
| `--non-interactive` | Auto-select title candidate #1 and subtitle #1 without prompting.          |
| `--force`           | Overwrite existing subtitles without asking.                                |
| `--dry-run`         | Print plan without execution (no files downloaded/written).                 |
| `--verbose`         | Print raw API response for debugging (max 500 chars).                      |
| `--version`         | Print tool version and exit.                                                |

### Example Commands

```bash
# Interactive mode — drag & drop
python3 subdl.py

# Download subtitle for 1 file
python3 subdl.py /media/movies/Inception.2010.mkv

# Scan entire folder recursively
python3 subdl.py /media/movies/

# Auto mode (non-interactive) + force overwrite
python3 subdl.py /media/movies/ --non-interactive --force

# Dry run — see what will be processed without downloading
python3 subdl.py /media/movies/ --dry-run

# Debug mode
python3 subdl.py /media/movies/Movie.mkv --verbose
```

---

## Changing Language

By default, SubDL downloads **Indonesian** subtitles (`--lang id`). You can download subtitles in other languages by passing the language code:

```bash
# Download English subtitles
python3 subdl.py /path/to/video.mkv --lang en

# Download Spanish subtitles
python3 subdl.py /path/to/video.mkv --lang es
```

Supported common codes include: `id` (Indonesian), `en` (English), `es` (Spanish), `fr` (French), `de` (German), etc. If a specific code is not mapped, the tool will pass the value directly to the SubSource API.

---

## Terminal Output Examples

### ✅ SUCCESS Scenario — 1 file successful, replace prompt answered `y`

```
🎬 Found 1 video file.

📂 [1/1] Inception.2010.1080p.BluRay.x264.mkv
⚠  Subtitle already exists for Inception.2010.1080p.BluRay.x264.mkv. Replace? (y/n): y
🔍 Searching: "Inception" (2010)...
Search results for "Inception":
  [1] Inception (2010) — Movie
  [2] Inception: The Cobol Job (2010) — Movie

Select [1-2] (default 1, 's' to skip): 1
📋 Selecting title: Inception (2010) — Movie
📑 Fetching subtitle list...
Subtitles available (3 total):
  [1] Inception.2010.1080p.BluRay.x264 | ⭐ 12/14 | HI: No | DL: 3421
  [2] Inception.2010.720p.WEB-DL | ⭐ 8/9 | HI: No | DL: 1205
  [3] Inception.2010.REMUX | ⭐ 5/6 | HI: Yes | DL: 890

Select [1-3] (default 1, 's' to skip): 1
⬇  Downloading subtitle #10124960...
✅ Saved: /media/movies/Inception.2010.1080p.BluRay.x264.srt

━━━━━━━━━━━━━━━━━━━━━
📊 Summary:
  ✅ Success   : 1
  ⏭  Skipped   : 0
  ❌ Failed    : 0
━━━━━━━━━━━━━━━━━━━━━
```

### ⏭ SKIP Scenario — subtitle already exists, user answered `n`

```
🎬 Found 2 video files.

📂 [1/2] Dune.Part.Two.2024.mkv
⚠  Subtitle already exists for Dune.Part.Two.2024.mkv. Replace? (y/n): n
⏭  Skip.

📂 [2/2] The.Batman.2022.mkv
🔍 Searching: "The Batman" (2022)...
Search results for "The Batman":
  [1] The Batman (2022) — Movie

Select [1-1] (default 1, 's' to skip): 1
📋 Selecting title: The Batman (2022) — Movie
📑 Fetching subtitle list...
Subtitles available (2 total):
  [1] The.Batman.2022.1080p.WEB-DL | ⭐ 10/11 | HI: No | DL: 5602
  [2] The.Batman.2022.2160p.UHD | ⭐ 7/8 | HI: No | DL: 2301

Select [1-2] (default 1, 's' to skip): 1
⬇  Downloading subtitle #9876543...
✅ Saved: /media/movies/The.Batman.2022.srt

━━━━━━━━━━━━━━━━━━━━━
📊 Summary:
  ✅ Success   : 1
  ⏭  Skipped   : 1
  ❌ Failed    : 0
━━━━━━━━━━━━━━━━━━━━━
```

### ❌ NO INDO SRT Scenario — search found but no Indonesian SRT subtitles available

```
🎬 Found 1 video file.

📂 [1/1] Obscure.Indie.Film.2024.mkv
🔍 Searching: "Obscure Indie Film" (2024)...
Search results for "Obscure Indie Film":
  [1] Obscure Indie Film (2024) — Movie

Select [1-1] (default 1, 's' to skip): 1
📋 Selecting title: Obscure Indie Film (2024) — Movie
📑 Fetching subtitle list...
  ❌ No Indonesian subtitles in SRT format.

━━━━━━━━━━━━━━━━━━━━━
📊 Summary:
  ✅ Success   : 0
  ⏭  Skipped   : 0
  ❌ Failed    : 1
━━━━━━━━━━━━━━━━━━━━━
```

---

## Troubleshooting

### ❌ API Key Error

```
❌ API key invalid or expired. Set env var: export SUBSOURCE_API_KEY=your_key
```

**Solution:**
1. Check if env var is set: `echo $SUBSOURCE_API_KEY`
2. Ensure the key is still valid in the SubSource dashboard
3. Regenerate key if needed

### ❌ Permission Denied

```
❌ Cannot write to /media/movies/Movie.srt: permission denied. Skip.
```

**Solution:**
1. Check folder permissions: `ls -la /media/movies/`
2. Run with `sudo` if necessary (caution!)
3. Or move video files to a writable folder

### ⏳ Rate Limit

```
⏳ Rate limited. Waiting 5s...
```

**Solution:**
- The tool automatically handles rate limits with retries.
- If it persists, reduce the number of files processed or wait a few minutes.
- SubSource rate limit: 60 req/min, 1800 req/hour, 7200 req/day.

### ⚠ Unexpected API Response

```
⚠  API response not as expected.
📝 Raw response saved to .subdl_debug_20250224_130000.json
```

**Solution:**
- Open the debug JSON file to inspect the response.
- SubSource API might have changed — check official [docs](https://subsource.net/api-docs).
- Report an issue if necessary.

---

## Jellyfin Naming Convention Note

This tool automatically follows the Jellyfin naming convention:

- **Subtitle filename = Video filename** with `.srt` extension
- **DOES NOT** add language suffixes (`.id`, `.ind`, `.eng`, etc.)
- Jellyfin will automatically detect the subtitle as "Unknown" language, but it can still be played.

Example resulting folder structure:

```
/media/movies/
├── Inception (2010)/
│   ├── Inception.2010.1080p.BluRay.mkv
│   └── Inception.2010.1080p.BluRay.srt    ← auto-recognized by Jellyfin
├── Dune Part Two (2024)/
│   ├── Dune.Part.Two.2024.2160p.WEB-DL.mkv
│   └── Dune.Part.Two.2024.2160p.WEB-DL.srt
```

> **Note:** If you want Jellyfin to display the subtitle language, you can manually rename it to `.id.srt` or `.ind.srt`. However, this tool defaults to NOT adding suffixes for maximum compatibility.

---

## API Reference

- SubSource API Docs: [https://subsource.net/api-docs](https://subsource.net/api-docs)
- .NET Wrapper (endpoint reference): [https://github.com/moviecollection/sub-source](https://github.com/moviecollection/sub-source)
- Base URL: `https://api.subsource.net`
- Auth: `X-API-Key` header

---

## License

MIT — Free to use and modify.
