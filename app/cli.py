"""flick-cli: client terminal untuk API /chat.

  flick-cli                  # mode interaktif
  flick-cli "buat hello.py"  # sekali jalan
"""
import argparse
import os
import sys

import requests

BANTUAN = "Perintah: /reset (hapus memori), /status, /help, /exit"


def main(argv=None):
    p = argparse.ArgumentParser(prog="flick-cli", description="Client terminal Flick AI Agent")
    p.add_argument("pesan", nargs="*", help="kirim satu pesan lalu keluar")
    p.add_argument("--url", default=os.getenv("API_URL", "http://localhost:8000"))
    p.add_argument("--key", default=os.getenv("API_KEY", ""), help="X-API-Key (default: env API_KEY)")
    p.add_argument("-s", "--session", default="cli")
    a = p.parse_args(argv)

    def api(method, path, **kw):
        r = requests.request(method, f"{a.url}{path}", headers={"X-API-Key": a.key}, timeout=1000, **kw)
        if not r.ok:
            raise requests.HTTPError(f"{r.status_code}: {r.text}")
        return r.json()

    def kirim(teks):
        print("⏳ berpikir...", file=sys.stderr)
        hasil = api("POST", "/chat", json={"message": teks, "session_id": a.session})
        for t in hasil["tool_calls"]:
            print(f"🔧 {t}")
        print(hasil["answer"])

    try:
        if a.pesan:
            kirim(" ".join(a.pesan))
            return
    except requests.RequestException as e:
        sys.exit(f"Error: {e}")

    print(f"🤖 Flick ({a.url}, session: {a.session}). {BANTUAN}")
    while True:
        try:
            teks = input("\n› ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        try:
            if teks in ("/exit", "/quit"):
                return
            elif teks == "/help":
                print(BANTUAN)
            elif teks == "/reset":
                api("DELETE", f"/sessions/{a.session}")
                print("Memori percakapan dihapus 🧹")
            elif teks == "/status":
                s = api("GET", "/status")
                print(f"Folder: {s['workdir']}\nBerkas: {s['files']}\nModel: {s['model']}\n"
                      f"Shell: {'aktif' if s['shell'] else 'mati'}")
            elif teks:
                kirim(teks)
        except requests.RequestException as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\n(dibatalkan)")


if __name__ == "__main__":
    main()
