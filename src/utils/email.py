import aiosmtplib
from email.message import EmailMessage


async def send_email(subject: str, recipient: str, body: str):
    message = EmailMessage()
    message["From"] = "noreply@example.com"
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname="smtp.example.com",
        port=587,
        username="smtp_user",
        password="smtp_password",
        start_tls=True,
    )
