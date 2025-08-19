import os, resend
resend.api_key = os.environ['RESEND_API_KEY']
r = resend.Emails.send({
    'from': 'Cloud Photo Share <no-reply@send.naugevault.com>',
    'to': ['youraddress@example.com'],
    'subject': 'Test from Resend',
    'html': '<p>It works!</p>',
    'reply_to': 'support@naugevault.com',
})
print('Sent:', getattr(r, 'id', r))
