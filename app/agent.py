import json
import os
import subprocess

import ollama
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

# ===== KONFIGURASI (dari environment) =====
WORKDIR = os.path.realpath(os.getenv("WORKDIR", "./workspace"))
SESSION_DIR = os.path.join(WORKDIR, ".sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

MODEL = os.getenv("MODEL", "qwen3.5:9b")
NUM_CTX = int(os.getenv("NUM_CTX", "8192"))
MAX_PESAN = 30
ALLOW_SHELL = os.getenv("ALLOW_SHELL", "false").lower() == "true"

# OLLAMA_HOST: http://localhost:11434 (lokal), http://ollama:11434 (docker), https://ollama.com (Ollama Cloud)
_api_key = os.getenv("OLLAMA_API_KEY")
client = ollama.Client(
    host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    headers={"Authorization": f"Bearer {_api_key}"} if _api_key else None,
    timeout=900,
)


# ===== TOOLS =====
def path_aman(nama):
    p = os.path.realpath(os.path.join(WORKDIR, nama))
    if p != WORKDIR and not p.startswith(WORKDIR + os.sep):
        raise ValueError("Path di luar folder proyek")
    return p


def list_files(folder: str = ".") -> str:
    """Menampilkan daftar file di folder proyek."""
    hasil = []
    for root, dirs, files in os.walk(path_aman(folder)):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        hasil += [os.path.relpath(os.path.join(root, f), WORKDIR)
                  for f in files if not f.startswith(".")]
    return "\n".join(sorted(hasil)[:200]) or "(folder kosong)"


def read_file(nama: str) -> str:
    """Membaca isi file di folder proyek."""
    with open(path_aman(nama), encoding="utf-8", errors="ignore") as f:
        return f.read()[:8000]


def write_file(nama: str, isi: str) -> str:
    """Membuat atau menimpa file di folder proyek."""
    p = path_aman(nama)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(isi)
    return f"Tersimpan: {nama} ({len(isi)} karakter)"


def run_shell(perintah: str) -> str:
    """Menjalankan perintah shell di folder proyek."""
    # shortcut: tanpa konfirmasi y/n seperti versi Telegram; aktifkan hanya di dalam container
    if not ALLOW_SHELL:
        return "Shell dinonaktifkan (set ALLOW_SHELL=true untuk mengaktifkan)"
    try:
        h = subprocess.run(perintah, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=300)
        out = h.stdout + h.stderr
    except subprocess.TimeoutExpired:
        out = "⏱️ Timeout 5 menit"
    return out[-2000:] or "(tidak ada output)"


def web_search(query: str) -> str:
    """Mencari informasi terbaru di internet, mengembalikan judul, link, dan ringkasan.

    Args:
        query: kata kunci pencarian
    """
    hasil = DDGS().text(query, max_results=5)
    return "\n\n".join(f"{h['title']}\n{h['href']}\n{h['body']}" for h in hasil) or "(tidak ada hasil)"


def web_fetch(url: str) -> str:
    """Membuka halaman web dan mengambil isi teksnya.

    Args:
        url: alamat lengkap halaman, diawali http:// atau https://
    """
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header"]):
        t.decompose()
    return " ".join(soup.get_text(" ").split())[:6000] or "(halaman kosong)"


TOOLS = {f.__name__: f for f in [list_files, read_file, write_file, run_shell, web_search, web_fetch]}


# ===== SESSION =====
def file_session(sid):
    # sid dari client: buang karakter selain alnum/-/_ supaya tidak bisa keluar folder
    return os.path.join(SESSION_DIR, "".join(c for c in sid if c.isalnum() or c in "-_") + ".json")


def load_session(sid):
    try:
        with open(file_session(sid), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_session(sid, history):
    with open(file_session(sid), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)


def reset_session(sid):
    if os.path.exists(file_session(sid)):
        os.remove(file_session(sid))


def potong(history):
    h = history[-MAX_PESAN:]
    while h and h[0].get("role") != "user":
        h = h[1:]
    return h


def system_prompt():
    return (f"Kamu asisten coding yang bekerja di folder {WORKDIR}. "
            "Gunakan tool list_files, read_file, write_file, dan run_shell untuk file. "
            "Gunakan web_search untuk mencari info terbaru, lalu web_fetch untuk membaca halamannya. "
            "Sebutkan link sumbernya. Jawab dalam Bahasa Indonesia, singkat dan jelas.")


# ===== AGENT LOOP =====
def jalankan_agent(pesan, sid, max_langkah=15):
    """Return (jawaban, daftar tool call yang dijalankan)."""
    history = load_session(sid)
    history.append({"role": "user", "content": pesan})
    jawaban = "⚠️ Berhenti: batas langkah tercapai"
    langkah = []

    for _ in range(max_langkah):
        messages = [{"role": "system", "content": system_prompt()}] + potong(history)
        msg = client.chat(model=MODEL, messages=messages, tools=list(TOOLS.values()),
                          options={"num_ctx": NUM_CTX}).message
        history.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            jawaban = msg.content
            break

        for call in msg.tool_calls:
            nama, args = call.function.name, call.function.arguments or {}
            langkah.append(f"{nama}({args})")
            try:
                hasil = TOOLS[nama](**args)
            except Exception as e:
                hasil = f"Error: {e}"
            history.append({"role": "tool", "content": str(hasil), "tool_name": nama})

    save_session(sid, history)
    return jawaban or "(jawaban kosong)", langkah
