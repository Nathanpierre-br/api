from random import choice
from typing import Union
from helpers.i18n import i18n
from .base import Base


class Errors:
    @staticmethod
    def UserStruck(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=230,
            html_status_code=403,
            api_message="You are currently on a timeout.",
            spent_time=spent_time,
        )

    @staticmethod
    def CantProcessData(lang: str = "en"):
        return Base.Answer(
            api_status_code=422422,
            html_status_code=422,
            api_message=i18n.get("errors.CantProcessData", lang=lang),
            spent_time=0,
        )

    @staticmethod
    def Custom(
        api_code: int,
        api_message: str = None,
        html_status_code: int = 400,
        spent_time: Union[int, float] = 0,
        lang: str = "en",
    ):
        return Base.Answer(
            api_status_code=api_code,
            html_status_code=html_status_code,
            api_message=api_message or i18n.get("errors.InvalidRequest", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def Exs9(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1000000,
            html_status_code=400,
            api_message=i18n.get("errors.Exs9", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def SUS(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=420024,
            html_status_code=420,
            api_message=i18n.get("errors.SUS", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def UnsupportedClient(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=100,
            html_status_code=400,
            api_message=i18n.get("errors.UnsupportedClient", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def ExpiredRequest(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=10501,
            html_status_code=400,
            api_message=i18n.get("errors.ExpiredRequest", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def ExpiredSession(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=105,
            html_status_code=440,
            api_message=i18n.get("errors.ExpiredSession", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InvalidSession(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=105,
            html_status_code=440,
            api_message=i18n.get("errors.InvalidSession", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InternalServerError(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=500,
            html_status_code=500,
            api_message=i18n.get("errors.InternalServerError", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InternalError(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Errors.InternalServerError(spent_time, lang=lang)

    @staticmethod
    def MailError(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=500,
            html_status_code=500,
            api_message=i18n.get("errors.MailError", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def WaitMinuteForAnotherCode(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=219,
            html_status_code=400,
            api_message=i18n.get("errors.WaitMinuteForAnotherCode", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def TooManyRequest(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=219,
            html_status_code=400,
            api_message=i18n.get("errors.TooManyRequest", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def Forbidden(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=403,
            html_status_code=403,
            api_message=i18n.get("errors.Forbidden", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def IpFrozen(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=403,
            html_status_code=403,
            api_message=i18n.get("errors.IpFrozen", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def OutdatedDevice(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=218,
            html_status_code=400,
            api_message=i18n.get("errors.OutdatedDevice", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InvalidPath(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=100,
            html_status_code=404,
            api_message=i18n.get("errors.InvalidPath", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def UnimplementedPath(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=103,
            html_status_code=400,
            api_message=i18n.get("errors.UnimplementedPath", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def PathUnderMaintenance(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=103,
            html_status_code=500,
            api_message=i18n.get("errors.PathUnderMaintenance", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def PathWorkingInvalid(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=103,
            html_status_code=500,
            api_message=i18n.get("errors.PathWorkingInvalid", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InvalidRequest(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=103,
            html_status_code=400,
            api_message=i18n.get("errors.InvalidRequest", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InvalidMediaContent(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=103,
            html_status_code=400,
            api_message=i18n.get("errors.InvalidMediaContent", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def NSFWContent(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=403,
            html_status_code=403,
            api_message=i18n.get("errors.NSFWContent", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def BigMediaContent(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=102,
            html_status_code=400,
            api_message=i18n.get("errors.BigMediaContent", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def NotEnoughCoins(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=2001,
            html_status_code=400,
            api_message=i18n.get("errors.NotEnoughCoins", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def AlreadyClaimed(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=2601,
            html_status_code=403,
            api_message=i18n.get("errors.AlreadyClaimed", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def LotteryPlayed(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=4400,
            html_status_code=403,
            api_message=i18n.get("errors.LotteryPlayed", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def LotteryNotAvailable(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=4400,
            html_status_code=403,
            api_message=i18n.get("errors.LotteryNotAvailable", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def BigMessage(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1664,
            html_status_code=400,
            api_message=i18n.get("errors.BigMessage", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def VerificationRequired(
        url: str, spent_time: Union[int, float] = 0, lang: str = "en"
    ):
        return Base.Answer(
            data={
                "url": url,
                "title": i18n.get("errors.VerificationRequired_Title", lang=lang),
                "okButtonText": i18n.get(
                    "errors.VerificationRequired_OkButtonText", lang=lang
                ),
                "cancelButtonText": i18n.get(
                    "errors.VerificationRequired_CancelButtonText", lang=lang
                ),
                "noCancelButton": False,
            },
            api_status_code=270,
            html_status_code=400,
            api_message=i18n.get("errors.VerificationRequired", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def IncorrectVerificationCode(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=3102,
            html_status_code=400,
            api_message=i18n.get("errors.IncorrectVerificationCode", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def EmailWasTaken(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=215,
            html_status_code=400,
            api_message=i18n.get("errors.EmailWasTaken", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def AminoIdWasTaken(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=215,
            html_status_code=400,
            api_message=i18n.get("errors.AminoIdWasTaken", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def NotWorkingEmail(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=215,
            html_status_code=400,
            api_message=i18n.get("errors.NotWorkingEmail", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InvalidEmail(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=215,
            html_status_code=400,
            api_message=i18n.get("errors.InvalidEmail", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def ExpiredVerificationCode(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=3103,
            html_status_code=400,
            api_message=i18n.get("errors.ExpiredVerificationCode", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InvalidVerificationCode(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=3104,
            html_status_code=400,
            api_message=i18n.get("errors.InvalidVerificationCode", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def VerificationCodeAlreadySent(
        spent_time: Union[int, float] = 0, lang: str = "en"
    ):
        return Base.Answer(
            api_status_code=3105,
            html_status_code=400,
            api_message=i18n.get("errors.VerificationCodeAlreadySent", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InvalidLogin(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=200,
            html_status_code=400,
            api_message=i18n.get("errors.InvalidLogin", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def AccountNotExist(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=216,
            html_status_code=400,
            api_message=i18n.get("errors.AccountNotExist", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def DataNotExist(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=107,
            html_status_code=400,
            api_message=i18n.get("errors.DataNotExist", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def AccountDisabled(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=201,
            html_status_code=400,
            api_message=i18n.get("errors.AccountDisabled", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def AccountDeleted(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=246,
            html_status_code=400,
            api_message=i18n.get("errors.AccountDeleted", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def UnverifiedEmail(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=246,
            html_status_code=400,
            api_message=i18n.get("errors.UnverifiedEmail", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def TooManyChatUsers(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1605,
            html_status_code=400,
            api_message=i18n.get("errors.TooManyChatUsers", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def TooManyInvitedUsers(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1606,
            html_status_code=400,
            api_message=i18n.get("errors.TooManyInvitedUsers", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def ChatInvitesForbidden(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1611,
            html_status_code=400,
            api_message=i18n.get("errors.ChatInvitesForbidden", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def RemovedFromChat(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1612,
            html_status_code=400,
            api_message=i18n.get("errors.RemovedFromChat", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def UserNotJoined(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1612,
            html_status_code=400,
            api_message=i18n.get("errors.UserNotJoined", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def MemberKickedByOrganizer(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1637,
            html_status_code=400,
            api_message=i18n.get("errors.MemberKickedByOrganizer", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def UserBanned(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=229,
            html_status_code=400,
            api_message=i18n.get("errors.UserBanned", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def UserUnavailable(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=225,
            html_status_code=400,
            api_message=i18n.get("errors.UserUnavailable", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def ViewModeEnabled(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1663,
            html_status_code=400,
            api_message=i18n.get("errors.ViewModeEnabled", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def ChatMessageTooBig(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1664,
            html_status_code=400,
            api_message=i18n.get("errors.ChatMessageTooBig", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def InvalidMessage(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=103,
            html_status_code=400,
            api_message=i18n.get("errors.InvalidMessage", lang=lang),
            spent_time=spent_time,
        )

    @staticmethod
    def NotEnoughRights(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=110,
            html_status_code=400,
            api_message=choice(i18n.get("errors.NotEnoughRights", lang=lang)),
            spent_time=spent_time,
        )

    @staticmethod
    def MythicData(spent_time: Union[int, float] = 0, lang: str = "en"):
        return Base.Answer(
            api_status_code=1600,
            html_status_code=400,
            api_message=choice(i18n.get("errors.MythicData", lang=lang)),
            spent_time=spent_time,
        )
