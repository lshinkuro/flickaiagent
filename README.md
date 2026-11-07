# Flick AI Agent

[![CI](https://github.com/lshinkuro/flickaiagent/actions/workflows/ci.yml/badge.svg)](https://github.com/lshinkuro/flickaiagent/actions/workflows/ci.yml)

AI coding agent (port dari versi Colab + Telegram) sebagai API **FastAPI**, dikelola dengan **uv**, model lewat **Ollama**, siap jalan di **Docker** / VPS.

📖 **Baru pertama kali? Baca [Panduan Pemakaian](docs/PANDUAN.md)** (langkah demi langkah: laptop, CLI, Telegram, Docker, VPS, troubleshooting).

Tools agent: `list_files`, `read_file`, `write_file`, `run_shell`, `web_search`, `web_fetch`. Semua operasi file dikunci di folder `WORKDIR`.

```
app/
  agent.py   # tools + session + agent loop (logika dari Colab)
  main.py    # endpoint FastAPI
  telegram_bot.py  # bot Telegram, client dari /chat
  cli.py     # flick-cli, client terminal dari /chat
tests/       # uv run --with pytest pytest
docs/PANDUAN.md  # panduan pemakaian lengkap
.github/workflows/ci.yml  # CI: test + build Docker
Dockerfile
docker-compose.yml
.env.example
```

## 1. Jalan lokal (uv)

```bash
# install Ollama: https://ollama.com/download, lalu
ollama pull qwen3.5:9b        # butuh RAM/VRAM ~8GB; kalau berat coba qwen3.5:4b

cp .env.example .env          # sesuaikan
uv sync
uv run uvicorn app.main:app --env-file .env --reload
```

Buka dokumentasi interaktif: http://localhost:8000/docs

## 2. Jalan pakai Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec ollama ollama pull qwen3.5:9b   # sekali saja, model tersimpan di volume
```

Compose menjalankan 3 service: `api`, `bot` (Telegram), `ollama`. Di dalam compose, `OLLAMA_HOST` otomatis `http://ollama:11434` dan `API_URL` bot otomatis `http://api:8000`. Kalau belum mau pakai bot: `docker compose up -d api ollama`. File hasil kerja agent ada di `./workspace`.

## 3. Bot Telegram

Bot ini hanya meneruskan pesan ke `/chat`, jadi API harus jalan dulu.

1. Buat bot di [@BotFather](https://t.me/BotFather), salin token ke `TELEGRAM_TOKEN` di `.env`.
2. Jalankan bot (lokal, di terminal kedua):
   ```bash
   uv run --env-file .env python -m app.telegram_bot
   ```
3. Kirim pesan apa saja ke bot. Bot membalas chat ID kamu; isi ke `ALLOWED_CHAT_ID` lalu restart bot.

Perintah: `/start`, `/help`, `/reset`, `/status`. Pesan lain dikirim ke agent; tool yang dipakai ditampilkan sebelum jawaban. Session memakai chat ID, jadi memori Telegram terpisah dari session lain.

## 4. flick-cli

Client terminal, juga memanggil `/chat` (API harus jalan).

```bash
uv run flick-cli                       # mode interaktif: /reset, /status, /help, /exit
uv run flick-cli "buat hello.py"       # sekali jalan

# pasang global supaya bisa dipanggil dari folder mana pun
uv tool install -e .
flick-cli --url https://agent.domainmu.com --key <API_KEY>
```

Alamat & key juga bisa lewat env `API_URL` dan `API_KEY`. Pakai `-s nama` untuk session terpisah (default `cli`).

## 5. Endpoint

| Method | Path | Fungsi |
|---|---|---|
| GET | `/health` | cek hidup |
| POST | `/chat` | `{"message": "...", "session_id": "default"}` → `{"answer", "tool_calls"}` |
| DELETE | `/sessions/{id}` | reset memori percakapan (pengganti `/reset`) |
| GET | `/status` | info folder kerja & model (pengganti `/status`) |

```bash
curl -X POST localhost:8000/chat \
  -H 'content-type: application/json' -H 'X-API-Key: <API_KEY>' \
  -d '{"message": "buatkan hello.py yang print halo"}'
```

Header `X-API-Key` hanya dicek kalau `API_KEY` diisi di `.env`.

## 6. Konfigurasi (`.env`)

| Variabel | Default | Keterangan |
|---|---|---|
| `MODEL` | `qwen3.5:9b` | model Ollama (harus support tool calling) |
| `NUM_CTX` | `8192` | panjang konteks |
| `OLLAMA_HOST` | `http://localhost:11434` | lokasi server Ollama |
| `OLLAMA_API_KEY` | – | untuk Ollama Cloud |
| `API_KEY` | – | proteksi endpoint, **wajib di VPS** |
| `WORKDIR` | `./workspace` | folder kerja agent |
| `ALLOW_SHELL` | `false` | izinkan `run_shell` |
| `TELEGRAM_TOKEN` | – | token dari BotFather |
| `ALLOWED_CHAT_ID` | – | hanya chat ini yang dilayani |
| `API_URL` | `http://localhost:8000` | alamat API untuk bot |

## 7. Deploy ke VPS (tanpa GPU)

Kode Python tidak perlu diubah, cukup `.env` (dan compose untuk opsi A). Pilih salah satu:

**A. Ollama Cloud (paling ringan, rekomendasi kalau tidak punya GPU)**
Model jalan di server Ollama, VPS cukup 1 vCPU / 1GB.
```env
OLLAMA_HOST=https://ollama.com
OLLAMA_API_KEY=<key dari ollama.com/settings/keys>
MODEL=<model cloud yang support tools, cek ollama.com/search?c=cloud>
API_KEY=<string acak panjang>
```
Lalu di `docker-compose.yml` hapus service `ollama`, `depends_on` di `api`, dan baris `OLLAMA_HOST` di `api`, kemudian `docker compose up -d --build`.

**B. Ollama di VPS pakai CPU**
Bisa, tapi lambat. Pakai model kecil (mis. `qwen3.5:4b` atau lebih kecil) dan VPS RAM ≥ 8GB. Compose dipakai apa adanya.

**C. VPS GPU / sewa GPU per jam** (RunPod, Vast.ai, dll.)
Uncomment blok `deploy.resources` di service `ollama`.

Checklist VPS:
- Isi `API_KEY`. Tanpa itu siapa pun bisa menyuruh agent menulis file.
- Taruh di belakang reverse proxy HTTPS (Caddy/Nginx), atau ubah port jadi `127.0.0.1:8000:8000` kalau hanya diakses lewat SSH tunnel.
- `ALLOW_SHELL=true` hanya di dalam container: agent bisa menjalankan perintah apa saja di container itu.

## Beda dengan versi Colab

- Agent sekarang REST API; bot Telegram jadi proses terpisah yang memanggil `/chat` (polling, tidak perlu domain/webhook).
- Notifikasi 🔧 tool dikirim sekaligus setelah agent selesai, bukan satu per satu.
- Konfirmasi `y/n` untuk `run_shell` diganti flag `ALLOW_SHELL` (container jadi sandbox-nya).
- Google Drive → folder `WORKDIR` (di Docker di-mount ke `./workspace`).
- Session per `session_id` disimpan di `WORKDIR/.sessions/`.
