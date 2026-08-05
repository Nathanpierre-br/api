import yaml
from helpers.config import Config


class __i18n_singleton:
    def __init__(self, path: str = "files/i18n"):
        self.data: dict = {}
        self.path: str = path
        self.reload()

    def reload(self, path: str | None = None):
        if path is not None:
            self.path = path

        if self.path is None:
            raise Exception("invalid path")

        for lang in Config.LANG_SEGMENTS:
            try:
                with open(f"{self.path}/{lang}.yaml", mode="r", encoding="utf-8") as f:
                    content = f.read()
                    self.data[lang] = yaml.safe_load(content)
            except Exception:
                print(f"No translation for {lang} since there is no {path}/{lang}.yaml")
        return

    def get(self, key: str, lang: str = "en") -> str:
        def _get_nested(data, path):
            for part in path.split("."):
                if isinstance(data, dict):
                    data = data.get(part)
                else:
                    return None
            return data

        lang_data = self.data.get(lang)
        if lang_data is None:
            lang_data = self.data.get("en", {})
        result = _get_nested(lang_data, key)

        if isinstance(result, list):
            return result

        if not isinstance(result, str) or not result:
            result = _get_nested(lang_data, "errors.no-i18n")
            if isinstance(result, str) and result:
                result = result.replace("{key}", key)

        if not isinstance(result, str) or not result:
            return key

        return result


i18n = __i18n_singleton()
