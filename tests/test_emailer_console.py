from importlib import reload

def test_send_email_console(monkeypatch, capsys):
    # Force console mode so no external calls or secrets are needed
    monkeypatch.setenv("EMAIL_MODE", "console")

    import app.emailer as emailer
    reload(emailer)

    res = emailer.send_email("demo@example.com", "Hi", "<p>hello</p>")
    out = capsys.readouterr().out

    assert isinstance(res, dict)
    assert res.get("mode") == "console"
    assert "DEV EMAIL (console)" in out
    assert "TO: demo@example.com" in out
