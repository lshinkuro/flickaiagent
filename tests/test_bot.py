import os
os.environ["TELEGRAM_TOKEN"] = "x"
os.environ["ALLOWED_CHAT_ID"] = "42"

from app import telegram_bot as bot


def test_proses(monkeypatch):
    terkirim, panggilan = [], []
    monkeypatch.setattr(bot, "kirim", lambda cid, t: terkirim.append((cid, t)))
    monkeypatch.setattr(bot, "api", lambda m, p, **kw: panggilan.append((m, p)) or {})

    bot.proses(7, "halo")
    assert terkirim[-1] == (7, "Maaf, bot ini privat.")

    bot.proses(42, "/reset@namabot")
    assert panggilan[-1] == ("DELETE", "/sessions/42")

    bot.proses(42, "/ngawur")
    assert "tidak dikenal" in terkirim[-1][1]
