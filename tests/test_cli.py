from app import cli


def test_sekali_jalan(monkeypatch, capsys):
    class R:
        ok = True
        def json(self): return {"answer": "beres", "tool_calls": ["write_file({})"]}

    dipanggil = {}
    monkeypatch.setattr(cli.requests, "request",
                        lambda m, url, **kw: dipanggil.update(m=m, url=url, json=kw["json"]) or R())
    cli.main(["--url", "http://x", "-s", "s1", "buat", "file"])

    assert dipanggil == {"m": "POST", "url": "http://x/chat", "json": {"message": "buat file", "session_id": "s1"}}
    assert capsys.readouterr().out == "🔧 write_file({})\nberes\n"
