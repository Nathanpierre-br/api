from re import match
from smtplib import SMTP

from httpx import AsyncClient
from redmail import EmailSender

from helpers.config import Config


class EmailProcessor:
    """
    Processor for validating and removing temp emails.
    You don't really want to use temp emails in social network don't you?
    """

    CANT_SEND_HERE = [
        # "icloud.com"
    ]

    PERMATRUSTED = [
        "gmail.com",
        "icloud.com",
        "hotmail.com",
        "outlook.com",
    ]

    @staticmethod
    def NotWorking(email: str) -> bool:
        """
        True if our mail server cant send code to provided email, False if bad
        """
        if not match(
            r"^([a-z0-9]+(?:[._-][a-z0-9]+)*)@([a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,})$",
            email,
        ):
            return False

        return email.partition("@")[2] in EmailProcessor.CANT_SEND_HERE

    @staticmethod
    async def Validate(email: str) -> bool:
        """
        True if email is good, False if bad
        """
        if EmailProcessor.NotWorking(email):
            return False

        # No need to check if permatrusted emails are disposable
        # (potential fix for #12)
        if email.partition("@")[2] in EmailProcessor.PERMATRUSTED:
            return True

        try:
            # timeout set to 10s to avoid thread blocking
            # (potential fix for #12)
            async with AsyncClient() as client:
                request = await client.get(
                    "https://disposable.debounce.io", {"email": email}, timeout=10
                )
                info = request.json()
        except Exception:
            info = {}

        return info.get("disposable", False)

    @staticmethod
    def SendEmail(
        email: str,
        subject: str,
        html: str,
        text: str | None = None,
        body_images: dict | None = None,
    ) -> bool:
        try:
            email = EmailSender(
                host=Config.SMTP_SERVER,
                port=Config.SMTP_PORT,
                username=Config.SMTP_USER,
                password=Config.SMTP_PSWD,
                use_starttls=Config.SMTP_STARTTLS,
                cls_smtp=SMTP,
            )
            email.domain_name = Config.SITE_DOMAIN
            email.send(
                sender=Config.SMTP_SNDR,
                subject=subject,
                receivers=[email],
                html=html,
                text=text,
                body_images=body_images,
            )
            return True
        except Exception as e:
            print(e)
            return False
