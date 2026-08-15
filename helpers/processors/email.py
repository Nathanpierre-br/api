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
    async def Validate(email: str) -> bool:
        """
        True if email is good, False if bad
        """

        # if not an email, return false
        if not match(
            r"^([a-z0-9]+(?:[._-][a-z0-9]+)*)@([a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,})$",
            email.lower(),
        ):
            return False

        # if we can't send email here, also return false
        if email.partition("@")[2] in EmailProcessor.CANT_SEND_HERE:
            return False

        # No need to check if permatrusted emails are disposable
        # (potential fix for #12)
        if email.partition("@")[2] in EmailProcessor.PERMATRUSTED:
            return True

        try:
            # timeout set to 10s to avoid thread blocking
            # (potential fix for #12)
            async with AsyncClient(timeout=10) as client:
                request = await client.get(
                    "https://disposable.debounce.io", params={"email": email}
                )
                info = request.json()
        except Exception:
            info = {}

        judge_said = info.get("disposable", "false").lower()
        return judge_said == "false"

    @staticmethod
    def SendEmail(
        receiver: str,
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
                receivers=[receiver],
                html=html,
                text=text,
                body_images=body_images,
            )
            return True
        except Exception as e:
            print(e)
            return False
