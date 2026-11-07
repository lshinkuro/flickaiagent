# Panduan Pemakaian Flick AI Agent

Panduan langkah demi langkah dari nol sampai agent bisa dipakai lewat browser, terminal (`flick-cli`), dan Telegram. Untuk ringkasan teknis, lihat [README](../README.md).

## Daftar isi

1. [Cara kerjanya](#1-cara-kerjanya)
2. [Persiapan](#2-persiapan)
3. [Menjalankan di laptop](#3-menjalankan-di-laptop)
4. [Memakai lewat browser](#4-memakai-lewat-browser)
5. [Memakai lewat terminal (flick-cli)](#5-memakai-lewat-terminal-flick-cli)
6. [Memakai lewat Telegram](#6-memakai-lewat-telegram)
7. [Menjalankan dengan Docker](#7-menjalankan-dengan-docker)
8. [Deploy ke VPS](#8-deploy-ke-vps)
9. [Contoh perintah ke agent](#9-contoh-perintah-ke-agent)
10. [Masalah yang sering muncul](#10-masalah-yang-sering-muncul)

---

## 1. Cara kerjanya

```
 flick-cli ─┐
 Telegram  ─┼──►  API FastAPI (/chat)  ──►  Agent  ──►  Ollama (model AI)
 Browser   ─┘                                 │
                                              └──►  tools: baca/tulis file, shell, cari di web
```

- **API** adalah pusatnya. CLI dan bot Telegram hanya mengirim pesan ke API, jadi **API harus jalan lebih dulu**.
- **Agent** menerima pesan, bertanya ke model, lalu menjalankan tools sampai tugas selesai.
- **Ollama** menjalankan model AI. Bisa di laptop, di Docker, atau di Ollama Cloud (untuk yang tidak punya GPU).
- Semua file yang dibuat agent ada di folder `workspace/`. Agent tidak bisa menyentuh file di luar folder itu.

## 2. Persiapan

| Butuh | Untuk apa | Cara pasang |
|---|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | menjalankan Python & dependensi | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Ollama](https://ollama.com/download) | menjalankan model AI di laptop | download dari situsnya |
| Git | mengambil kode | biasanya sudah ada |
| Docker *(opsional)* | jalan dalam container / VPS | [docs.docker.com](https://docs.docker.com/get-docker/) |

Spesifikasi laptop untuk model `qwen3.5:9b`: RAM minimal 16GB (atau GPU dengan VRAM 8GB). Kalau laptop lebih kecil, pakai model yang lebih kecil (lihat [bagian 10](#10-masalah-yang-sering-muncul)) atau Ollama Cloud.

## 3. Menjalankan di laptop

**Langkah 1: ambil kode dan pasang dependensi**

```bash
git clone https://github.com/lshinkuro/flickaiagent.git
cd flickaiagent
uv sync
```

**Langkah 2: siapkan model**

Pastikan aplikasi Ollama sudah jalan, lalu:

```bash
ollama pull qwen3.5:9b
```

**Langkah 3: buat file konfigurasi**

```bash
cp .env.example .env
```

Untuk di laptop, isi bawaannya sudah cukup. Penjelasan tiap variabel ada di [README](../README.md#6-konfigurasi-env).

**Langkah 4: jalankan API**

```bash
uv run uvicorn app.main:app --env-file .env --reload
```

Kalau berhasil, muncul `Uvicorn running on http://127.0.0.1:8000`. Biarkan terminal ini tetap terbuka.

**Langkah 5: cek**

```bash
curl http://localhost:8000/health
# {"ok":true}
```

## 4. Memakai lewat browser

Buka **http://localhost:8000/docs**. Halaman ini otomatis dibuat FastAPI.

1. Klik `POST /chat` → **Try it out**.
2. Isi body:
   ```json
   { "message": "buatkan file hello.py yang print halo dunia", "session_id": "coba" }
   ```
3. Klik **Execute**. Jawaban agent ada di `answer`, dan tools yang dipakai ada di `tool_calls`.

Kalau `API_KEY` di `.env` diisi, isi juga kolom `x-api-key` di form tersebut. Atau pakai `curl`:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'content-type: application/json' \
  -H 'X-API-Key: ISI_API_KEY' \
  -d '{"message": "halo"}'
```

## 5. Memakai lewat terminal (flick-cli)

Buka **terminal kedua** (API di terminal pertama tetap jalan).

**Mode ngobrol (interaktif):**

```bash
uv run flick-cli
```

```
🤖 Flick (http://localhost:8000, session: cli). Perintah: /reset (hapus memori), /status, /help, /exit

› buatkan hello.py yang print halo
⏳ berpikir...
🔧 write_file({'nama': 'hello.py', 'isi': 'print("halo")'})
File hello.py sudah dibuat di workspace.

› /exit
```

**Perintah di dalam CLI:**

| Perintah | Fungsi |
|---|---|
| `/reset` | hapus memori percakapan, mulai dari awal |
| `/status` | lihat folder kerja, jumlah file, model, status shell |
| `/help` | daftar perintah |
| `/exit` atau Ctrl+D | keluar |

**Mode sekali jalan** (cocok untuk script):

```bash
uv run flick-cli "jelaskan isi hello.py"
```

**Pilihan tambahan:**

```bash
uv run flick-cli -s proyek-a          # session terpisah, memori tidak campur
uv run flick-cli --url http://IP-VPS:8000 --key ISI_API_KEY   # pakai API di server
```

**Pasang supaya bisa dipanggil dari mana saja:**

```bash
uv tool install -e .
flick-cli                       # sekarang tanpa "uv run"
```

Supaya tidak perlu mengetik `--url` dan `--key` terus, simpan di shell (`~/.zshrc` atau `~/.bashrc`):

```bash
export API_URL=https://agent.domainmu.com
export API_KEY=ISI_API_KEY
```

## 6. Memakai lewat Telegram

**Langkah 1: buat bot**

1. Buka [@BotFather](https://t.me/BotFather) di Telegram, kirim `/newbot`.
2. Ikuti instruksinya (nama bot, username yang berakhiran `bot`).
3. Salin token yang diberikan, tempel di `.env`:
   ```env
   TELEGRAM_TOKEN=123456789:AA...
   ```

**Langkah 2: jalankan bot** (terminal kedua, API tetap jalan)

```bash
uv run --env-file .env python -m app.telegram_bot
```

**Langkah 3: kunci bot hanya untuk kamu**

1. Kirim pesan apa saja ke bot kamu di Telegram.
2. Bot membalas: `Chat ID kamu: 12345678`.
3. Isi ke `.env`:
   ```env
   ALLOWED_CHAT_ID=12345678
   ```
4. Hentikan bot (Ctrl+C) lalu jalankan lagi.

Sekarang orang lain yang mengirim pesan hanya akan dapat balasan "Maaf, bot ini privat."

**Perintah bot:** `/start`, `/help`, `/reset` (hapus memori), `/status`. Pesan selain itu dikerjakan agent. Selama agent bekerja, bot menampilkan "typing…". Kalau kamu kirim pesan baru sebelum selesai, bot membalas "⏳ Masih mengerjakan tugas sebelumnya".

## 7. Menjalankan dengan Docker

Satu perintah untuk menjalankan API, bot Telegram, dan Ollama sekaligus:

```bash
cp .env.example .env              # isi TELEGRAM_TOKEN dkk.
docker compose up -d --build
docker compose exec ollama ollama pull qwen3.5:9b    # sekali saja
```

Perintah sehari-hari:

```bash
docker compose ps                 # lihat service yang jalan
docker compose logs -f api        # lihat log API (ganti api → bot / ollama)
docker compose restart bot        # restart bot setelah ubah .env
docker compose down               # matikan semua
```

Belum mau pakai bot? Jalankan sebagian saja: `docker compose up -d api ollama`.

File buatan agent tetap tersimpan di folder `./workspace` di laptop/server kamu walau container dimatikan.

## 8. Deploy ke VPS

Kalau tidak punya GPU, cara paling hemat adalah **VPS kecil + Ollama Cloud**: VPS hanya menjalankan API dan bot, sedangkan modelnya jalan di server Ollama.

**Langkah 1: siapkan VPS** (Ubuntu, 1 vCPU / 1GB sudah cukup)

```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/lshinkuro/flickaiagent.git
cd flickaiagent
cp .env.example .env
```

**Langkah 2: isi `.env`**

```env
OLLAMA_HOST=https://ollama.com
OLLAMA_API_KEY=key-dari-ollama.com/settings/keys
MODEL=nama-model-cloud-yang-support-tools
API_KEY=string-acak-panjang          # buat dengan: openssl rand -hex 32
TELEGRAM_TOKEN=...
ALLOWED_CHAT_ID=...
```

**Langkah 3: sesuaikan `docker-compose.yml`**

Karena model ada di cloud, hapus:
- seluruh service `ollama` (dan `volumes: ollama:` di paling bawah),
- `depends_on: - ollama` di service `api`,
- baris `OLLAMA_HOST: http://ollama:11434` di service `api`.

**Langkah 4: jalankan**

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

**Langkah 5: amankan**

- `API_KEY` **wajib diisi**. Tanpa itu, siapa pun yang tahu IP VPS kamu bisa menyuruh agent menulis file.
- Pakai HTTPS. Cara termudah dengan [Caddy](https://caddyserver.com/): arahkan domain ke VPS lalu `caddy reverse-proxy --from agent.domainmu.com --to localhost:8000`.
- Kalau hanya dipakai lewat Telegram, API tidak perlu dibuka ke internet. Ubah port di compose jadi `"127.0.0.1:8000:8000"`.

Pilihan lain (Ollama pakai CPU di VPS, atau sewa GPU) ada di [README](../README.md#7-deploy-ke-vps-tanpa-gpu).

## 9. Contoh perintah ke agent

| Kebutuhan | Contoh pesan |
|---|---|
| Buat file | `buatkan script python untuk rename semua file .jpg jadi foto_1.jpg, foto_2.jpg, dst` |
| Baca & jelaskan | `jelaskan isi file main.py` |
| Perbaiki kode | `di app.py ada error IndexError di baris 20, perbaiki` |
| Lihat proyek | `file apa saja yang ada di workspace?` |
| Cari info terbaru | `cari versi terbaru FastAPI dan apa yang baru, sertakan link` |
| Baca halaman web | `baca https://docs.astral.sh/uv/ lalu ringkas cara install` |
| Jalankan kode* | `jalankan hello.py dan tunjukkan outputnya` |

\* Butuh `ALLOW_SHELL=true` di `.env`. Aktifkan **hanya di Docker**, karena agent bisa menjalankan perintah apa saja tanpa konfirmasi.

Tips:
- Agent ingat percakapan sebelumnya dalam session yang sama. Pakai `/reset` kalau ganti topik supaya jawabannya tidak melantur.
- Beri instruksi spesifik (nama file, bahasa, format) supaya hasilnya sesuai.

## 10. Masalah yang sering muncul

| Gejala | Penyebab & solusi |
|---|---|
| `Failed to connect to Ollama` | Ollama belum jalan. Buka aplikasi Ollama atau jalankan `ollama serve`. Di Docker: cek `docker compose ps`. |
| `model "qwen3.5:9b" not found` | Model belum di-download: `ollama pull qwen3.5:9b` (di Docker: `docker compose exec ollama ollama pull ...`). |
| Jawaban sangat lambat / laptop panas | Model terlalu besar untuk hardware. Ganti `MODEL` ke yang lebih kecil, misalnya `qwen3.5:4b`, atau pakai Ollama Cloud. |
| Agent tidak memakai tools, cuma ngobrol | Model tidak mendukung tool calling. Pilih model berlabel **tools** di [ollama.com/search](https://ollama.com/search?c=tools). |
| `401: API key salah` | `--key` / header `X-API-Key` tidak sama dengan `API_KEY` di `.env` server. |
| `Connection refused` dari CLI / bot | API belum jalan, atau `API_URL` salah. Cek `curl http://localhost:8000/health`. |
| Bot Telegram diam saja | Cek `TELEGRAM_TOKEN`, lalu lihat log bot (`docker compose logs -f bot`). Pastikan bot tidak jalan di dua tempat sekaligus (misal di Colab dan di laptop). |
| Bot membalas "bot ini privat" ke kamu | `ALLOWED_CHAT_ID` salah. Kosongkan, restart bot, kirim pesan untuk melihat chat ID yang benar. |
| `Shell dinonaktifkan` | Disengaja. Set `ALLOW_SHELL=true` (sebaiknya hanya di Docker). |
| `⚠️ Berhenti: batas langkah tercapai` | Tugas terlalu besar untuk 15 langkah. Pecah jadi beberapa pesan yang lebih kecil. |
