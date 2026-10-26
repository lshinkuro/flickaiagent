"""Bot Telegram: client tipis yang meneruskan pesan ke API /chat.

Jalankan: uv run --env-file .env python -m app.telegram_bot
"""
import os
import threading
import time

import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
TG = f"https://api.telegram.org/bot{TOKEN}"
API_URL = os.getenv("API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.getenv("API_KEY", "")}
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID") or 0) or None

SIBUK = threading.Lock()


# ===== FUNGSI TELEGRAM =====
def kirim(chat_id, teks):
    teks = teks or "(jawaban kosong)"
    for i in range(0, len(teks), 4000):
        requests.post(f"{TG}/sendMessage", json={"chat_id": chat_id, "text": teks[i:i+4000]}, timeout=20)


def tetap_mengetik(chat_id, stop):
    while not stop.is_set():
        try:
            requests.post(f"{TG}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=10)
        except requests.RequestException:
            pass
        stop.wait(4)


def api(method, path, **kw):
    r = requests.request(method, f"{API_URL}{path}", headers=HEADERS, timeout=1000, **kw)
    r.raise_for_status()
    return r.json()


# ===== KERJAKAN PESAN =====
def kerjakan(cid, teks):
    stop = threading.Event()
    threading.Thread(target=tetap_mengetik, args=(cid, stop), daemon=True).start()
    try:
        hasil = api("POST", "/chat", json={"message": teks, "session_id": str(cid)})
        if hasil["tool_calls"]:
            kirim(cid, "\n".join(f"🔧 {t}" for t in hasil["tool_calls"]))
        kirim(cid, hasil["answer"])
    except Exception as e:
        kirim(cid, f"Error: {e}")
    finally:
        stop.set()
        SIBUK.release()


# ===== COMMAND HANDLER =====
BANTUAN = ("Daftar Perintah:\n/start - Memulai bot\n/help - Bantuan\n"
           "/reset - Menghapus memori percakapan\n/status - Status proyek")


def cmd_start(cid):
    kirim(cid, "Halo! Saya AI Coding Agent milikmu. Kirim instruksi coding atau pakai perintah.\n\n" + BANTUAN)


def cmd_help(cid):
    kirim(cid, BANTUAN)


def cmd_reset(cid):
    api("DELETE", f"/sessions/{cid}")
    kirim(cid, "Memori percakapan telah dihapus 🧹")


def cmd_status(cid):
    s = api("GET", "/status")
    kirim(cid, f"ℹ️ Status Proyek:\nFolder: {s['workdir']}\nJumlah berkas: {s['files']}\n"
               f"Model: {s['model']}\nShell: {'aktif' if s['shell'] else 'mati'}")


COMMANDS = {"/start": cmd_start, "/help": cmd_help, "/reset": cmd_reset, "/status": cmd_status}


def proses(cid, teks):
    if ALLOWED_CHAT_ID is None:
        return kirim(cid, f"Chat ID kamu: {cid}\nIsi ALLOWED_CHAT_ID={cid} di .env, lalu restart bot.")
    if cid != ALLOWED_CHAT_ID:
        return kirim(cid, "Maaf, bot ini privat.")

    if teks.startswith("/"):
        cmd = teks.split()[0].split("@")[0].lower()
        if cmd not in COMMANDS:
            return kirim(cid, f"Perintah {cmd} tidak dikenal. Ketik /help.")
        try:
            COMMANDS[cmd](cid)
        except Exception as e:
            kirim(cid, f"Error: {e}")
        return

    if not SIBUK.acquire(blocking=False):
        return kirim(cid, "⏳ Masih mengerjakan tugas sebelumnya, tunggu ya.")
    threading.Thread(target=kerjakan, args=(cid, teks), daemon=True).start()


# ===== LOOP UTAMA =====
def main():
    offset = 0
    print(f"🤖 Bot berjalan, API: {API_URL}")
    while True:
        try:
            r = requests.get(f"{TG}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=40).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message")
                if m and "text" in m:
                    print(f"📩 {m['chat']['id']}: {m['text']}")
                    proses(m["chat"]["id"], m["text"].strip())
        except Exception as e:
            print("Koneksi error, mencoba lagi:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
