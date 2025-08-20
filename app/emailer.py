def verification_email_html(verify_url: str) -> str:
    btn_style = (
        "display:inline-block;padding:10px 16px;border-radius:6px;"
        "background:#111;color:#fff;text-decoration:none"
    )
    return (
        "<h2>Verify your email</h2>"
        "<p>Click the button below to verify your account.</p>"
        f'<p><a href="{verify_url}" style="{btn_style}">Verify Email</a></p>'
        f"<p>If the button doesn’t work, open this link:<br>{verify_url}</p>"
    )


def reset_email_html(reset_url: str) -> str:
    btn_style = (
        "display:inline-block;padding:10px 16px;border-radius:6px;"
        "background:#111;color:#fff;text-decoration:none"
    )
    return (
        "<h2>Reset your password</h2>"
        "<p>We received a request to reset your password.</p>"
        f'<p><a href="{reset_url}" style="{btn_style}">Reset Password</a></p>'
        "<p>If you didn’t request this, you can ignore this email.</p>"
        f"<p>Direct link: {reset_url}</p>"
    )
