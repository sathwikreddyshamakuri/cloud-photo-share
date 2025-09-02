import os, resend

resend.api_key = os.environ["RESEND_API_KEY"]

resp = resend.Emails.send({
    "from": "Cloud Photo Share <noreply@mail.naugevault.com>",
    "to": ["shyamakurisathwik@gmail.com"],
    "subject": "Cloud Photo Share test",
    "html": "<p>It works ✅</p>"
})
print(resp)
