import yaml


class __i18n_singleton:
    def __init__(self, path: str = "files/i18n.yaml"):
        self.data: dict = {}
        self.path: str = path
        self.reload()

    def reload(self, path: str | None = None):
        if path is not None:
            self.path = path

        if self.path is None:
            raise Exception("invalid path")

        with open(self.path, mode="r", encoding="utf-8") as f:
            content = f.read()
            self.data = yaml.safe_load(content)

        return

    def get(self, key: str, lang: str = "en") -> str:
        def _get_nested(data, path):
            for part in path.split("."):
                if isinstance(data, dict):
                    data = data.get(part)
                else:
                    return None
            return data

        lang_data = self.data.get(lang, {})
        result = _get_nested(lang_data, key)

        if not isinstance(result, str) or not result:
            result = _get_nested(lang_data, "errors.no-i18n")
            if isinstance(result, str) and result:
                result = result.replace("{key}", key)

        if not isinstance(result, str) or not result:
            return key

        return result


i18n = __i18n_singleton()
