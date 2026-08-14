class PlatformType:
    ANDROID: str = "android"
    IOS: str = "ios"

    META = {
        ANDROID: {"name": ANDROID, "suffix": ".apk", "marker": ""},
        IOS: {"name": IOS, "suffix": ".ipa", "marker": "ios"},
    }

    ALIASES = {"apk": ANDROID, "ipa": IOS}

    @classmethod
    def resolve(cls, name: str) -> dict | None:
        return cls.META.get(cls.ALIASES.get(name, name))
