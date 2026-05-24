from re import match

from requests import get


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
    def Validate(email: str) -> bool:
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
            info = get(
                "https://disposable.debounce.io", {"email": email}, timeout=10
            ).json()
        except Exception:
            info = {}

        return info.get("disposable", False)
