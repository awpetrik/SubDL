# SubSource Sub Downloader (`subdl`)

<p align="center">
<img width="1206" height="860" alt="image" src="https://github.com/user-attachments/assets/e68cabb4-ec28-43f7-af97-1a3aab3afa01" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Requests-066F24?style=for-the-badge&logo=python&logoColor=white" alt="Requests" />
  <img src="https://img.shields.io/badge/Rich-000000?style=for-the-badge&logo=python&logoColor=white" alt="Rich" />
</p>

[English](README_EN.md) | Bahasa Indonesia

CLI tool untuk download subtitle Indonesia dari [SubSource.net](https://subsource.net) 

Nama file subtitle otomatis match PERSIS dengan nama file video (hanya beda ekstensi), sehingga Jellyfin langsung auto-recognize tanpa konfigurasi tambahan.

```
Movie.2025.1080p.WEB-DL.mkv  →  Movie.2025.1080p.WEB-DL.srt
```

---

## Quick Install (EXPERIMENTAL)

Jalankan satu perintah — otomatis cek Python, install dependencies, dan langsung jalan:

**Linux / macOS:** (Tested on Linux)
```bash
curl -sSL https://rivaldi.space/SubDL | bash
```

**Windows (PowerShell):** (Belum di test, please tell me if it doesn't works or error)
```powershell
irm https://rivaldi.space/SubDLWin | iex
```

> Script akan menginstall SubDL ke `~/.subdl/` (Linux/macOS) atau `%USERPROFILE%\.subdl\` (Windows) dengan virtual environment di dalamnya. Installer juga akan **otomatis menambahkan `subdl` ke PATH**, sehingga kamu bisa langsung menjalankannya dari terminal manapun.

---

## Manual Install

Jika lebih suka install manual:

- **Python 3.9+**
- **pip** (Python package manager)

```bash
git clone https://github.com/awpetrik/SubDL.git
cd SubDL
pip install -r requirements.txt
python3 subdl.py
```

Dependencies: hanya `requests` — tidak ada dependency tambahan di luar standard library.

---

## API Key

Saat pertama kali menjalankan SubDL, kamu akan diminta memasukkan API key:

```
🔑 API Key belum dikonfigurasi.

Cara mendapatkan API key:
  1. Buka https://subsource.net
  2. Login atau buat akun
  3. Klik Profile → API Key
  4. Copy API key yang ditampilkan

Paste API key di sini: ********
✅ API key tersimpan di: ~/.subdl/config
```

API key otomatis tersimpan — **tidak perlu input ulang** di lain waktu.

### Alternatif: Environment Variable

```bash
# Linux / macOS
export SUBSOURCE_API_KEY=your_key_here

# Windows CMD
set SUBSOURCE_API_KEY=your_key_here

# PowerShell
$env:SUBSOURCE_API_KEY="your_key_here"
```

> Environment variable selalu diutamakan jika di-set (override config file).

---

## Usage

### Mode Interaktif (Drag & Drop)

Cukup jalankan tanpa argumen:

```bash
python3 subdl.py
```

Lalu **drag & drop** file video atau folder ke terminal, tekan Enter:

```
┌─────────────────────────────────────────────┐
│  🎬 SubSource Sub Downloader by awpetrik    │
│  Download subtitle Indonesia secara instan  │
│     https://github.com/awpetrik/SubDL       │
└─────────────────────────────────────────────┘

📂 Drag & drop file video atau folder ke sini, lalu tekan Enter:

   ▸ /media/movies/Inception.2010.mkv
```

> 💡 **Tip:** Di kebanyakan terminal (GNOME Terminal, Konsole, Windows Terminal, iTerm2), cukup drag file dari file manager dan drop ke jendela terminal — path otomatis terisi.

### Mode CLI (Langsung)

Bisa juga langsung pass path sebagai argumen:

```bash
python3 subdl.py <path> [options]
```

### Flags

| Flag                | Deskripsi                                                                  |
|---------------------|----------------------------------------------------------------------------|
| `--lang LANG`       | Kode bahasa, default: `id`. Saat ini hanya `id` yang diimplementasi penuh. |
| `--non-interactive` | Auto-pilih kandidat judul #1 dan subtitle #1 tanpa prompt.                 |
| `--force`           | Overwrite subtitle yang sudah ada tanpa tanya.                             |
| `--dry-run`         | Print rencana tanpa eksekusi (tidak download/tulis file apapun).           |
| `--verbose`         | Print raw API response untuk debugging (max 500 char).                     |
| `--version`         | Print versi tool dan exit.                                                 |

### Contoh Perintah

```bash
# Mode interaktif — drag & drop
python3 subdl.py

# Download subtitle untuk 1 file
python3 subdl.py /media/movies/Inception.2010.mkv

# Scan seluruh folder recursive
python3 subdl.py /media/movies/

# Auto mode (non-interactive) + force overwrite
python3 subdl.py /media/movies/ --non-interactive --force

# Dry run — lihat apa yang akan diproses tanpa download
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

## Contoh Output Terminal

### ✅ Skenario SUCCESS — 1 file berhasil, replace prompt dijawab `y`

```
🎬 Ditemukan 1 file video.

📂 [1/1] Inception.2010.1080p.BluRay.x264.mkv
⚠  Subtitle sudah ada untuk Inception.2010.1080p.BluRay.x264.mkv. Replace? (y/n): y
🔍 Mencari: "Inception" (2010)...
Hasil pencarian untuk "Inception":
  [1] Inception (2010) — Movie
  [2] Inception: The Cobol Job (2010) — Movie

Pilih [1-2] (default 1, 's' untuk skip): 1
📋 Memilih judul: Inception (2010) — Movie
📑 Mengambil daftar subtitle...
Subtitle tersedia (3 total):
  [1] Inception.2010.1080p.BluRay.x264 | ⭐ 12/14 | HI: No | DL: 3421
  [2] Inception.2010.720p.WEB-DL | ⭐ 8/9 | HI: No | DL: 1205
  [3] Inception.2010.REMUX | ⭐ 5/6 | HI: Yes | DL: 890

Pilih [1-3] (default 1, 's' untuk skip): 1
⬇  Mengunduh subtitle #10124960...
✅ Tersimpan: /media/movies/Inception.2010.1080p.BluRay.x264.srt

━━━━━━━━━━━━━━━━━━━━━
📊 Ringkasan:
  ✅ Sukses   : 1
  ⏭  Dilewati : 0
  ❌ Gagal    : 0
━━━━━━━━━━━━━━━━━━━━━
```

### ⏭ Skenario SKIP — subtitle sudah ada, user jawab `n`

```
🎬 Ditemukan 2 file video.

📂 [1/2] Dune.Part.Two.2024.mkv
⚠  Subtitle sudah ada untuk Dune.Part.Two.2024.mkv. Replace? (y/n): n
⏭  Skip.

📂 [2/2] The.Batman.2022.mkv
🔍 Mencari: "The Batman" (2022)...
Hasil pencarian untuk "The Batman":
  [1] The Batman (2022) — Movie

Pilih [1-1] (default 1, 's' untuk skip): 1
📋 Memilih judul: The Batman (2022) — Movie
📑 Mengambil daftar subtitle...
Subtitle tersedia (2 total):
  [1] The.Batman.2022.1080p.WEB-DL | ⭐ 10/11 | HI: No | DL: 5602
  [2] The.Batman.2022.2160p.UHD | ⭐ 7/8 | HI: No | DL: 2301

Pilih [1-2] (default 1, 's' untuk skip): 1
⬇  Mengunduh subtitle #9876543...
✅ Tersimpan: /media/movies/The.Batman.2022.srt

━━━━━━━━━━━━━━━━━━━━━
📊 Ringkasan:
  ✅ Sukses   : 1
  ⏭  Dilewati : 1
  ❌ Gagal    : 0
━━━━━━━━━━━━━━━━━━━━━
```

### ❌ Skenario NO INDO SRT — search ketemu tapi tidak ada subtitle Indonesia SRT

```
🎬 Ditemukan 1 file video.

📂 [1/1] Obscure.Indie.Film.2024.mkv
🔍 Mencari: "Obscure Indie Film" (2024)...
Hasil pencarian untuk "Obscure Indie Film":
  [1] Obscure Indie Film (2024) — Movie

Pilih [1-1] (default 1, 's' untuk skip): 1
📋 Memilih judul: Obscure Indie Film (2024) — Movie
📑 Mengambil daftar subtitle...
  ❌ Tidak ada subtitle Indonesia format SRT.

━━━━━━━━━━━━━━━━━━━━━
📊 Ringkasan:
  ✅ Sukses   : 0
  ⏭  Dilewati : 0
  ❌ Gagal    : 1
━━━━━━━━━━━━━━━━━━━━━
```

---

## Troubleshooting

### ❌ API Key Error

```
❌ API key invalid atau expired. Set env var: export SUBSOURCE_API_KEY=your_key
```

**Solusi:**
1. Cek apakah env var sudah di-set: `echo $SUBSOURCE_API_KEY`
2. Pastikan key masih valid di dashboard SubSource
3. Regenerate key jika perlu

### ❌ Permission Denied

```
❌ Tidak bisa tulis ke /media/movies/Movie.srt: permission denied. Skip.
```

**Solusi:**
1. Cek permission folder: `ls -la /media/movies/`
2. Jalankan dengan `sudo` jika perlu (hati-hati!)
3. Atau pindahkan file video ke folder yang writable

### ⏳ Rate Limit

```
⏳ Rate limited. Tunggu 5s...
```

**Solusi:**
- Tool otomatis menangani rate limit dengan retry
- Jika terus terjadi, kurangi jumlah file yang diproses atau tunggu beberapa menit
- Rate limit SubSource: 60 req/menit, 1800 req/jam, 7200 req/hari

### ⚠ Response API Tidak Sesuai

```
⚠  Response API tidak sesuai ekspektasi.
📝 Raw response disimpan ke .subdl_debug_20250224_130000.json
```

**Solusi:**
- Buka file debug JSON untuk inspeksi response
- Mungkin API SubSource telah berubah — cek [docs resmi](https://subsource.net/api-docs)
- Laporkan issue jika diperlukan

---

## Catatan Jellyfin Naming Convention

Tool ini secara otomatis mengikuti Jellyfin naming convention:

- **Subtitle filename = Video filename** dengan ekstensi `.srt`
- **TIDAK** menambahkan suffix bahasa (`.id`, `.ind`, `.eng`, dll)
- Jellyfin akan otomatis mendeteksi subtitle sebagai "Unknown" language, tapi tetap bisa diputar

Contoh struktur folder yang dihasilkan:

```
/media/movies/
├── Inception (2010)/
│   ├── Inception.2010.1080p.BluRay.mkv
│   └── Inception.2010.1080p.BluRay.srt    ← auto-recognized oleh Jellyfin
├── Dune Part Two (2024)/
│   ├── Dune.Part.Two.2024.2160p.WEB-DL.mkv
│   └── Dune.Part.Two.2024.2160p.WEB-DL.srt
```

> **Catatan:** Jika ingin Jellyfin menampilkan bahasa subtitle, bisa rename manual ke `.id.srt` atau `.ind.srt`. Tapi default tool ini sengaja TIDAK menambahkan suffix untuk kompatibilitas maksimal.

---

## Referensi API

- SubSource API Docs: [https://subsource.net/api-docs](https://subsource.net/api-docs)
- .NET Wrapper (referensi endpoint): [https://github.com/moviecollection/sub-source](https://github.com/moviecollection/sub-source)
- Base URL: `https://api.subsource.net`
- Auth: `X-API-Key` header

---

## License

MIT — Free to use and modify.
