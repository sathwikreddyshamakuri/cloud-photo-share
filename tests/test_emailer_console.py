import os
from importlib import reload

def test_send_email_console(monkeypatch, capsys):
    # Force console mode so no external calls or secrets are needed
    monkeypatch.setenv("EMAIL_MODE", "console")
    # Ensure module reads the new env
    import app.emailer as emailer
    reload(emailer)

    res = emailer.send_email("demo@example.com", "Hi", "<p>hello</p>")
    captured = capsys.readouterr().out

    assert isinstance(res, dict)
    assert res.get("mode") == "console"
    assert "DEV EMAIL (console)" in captured
    assert "TO: demo@example.com" in captured
