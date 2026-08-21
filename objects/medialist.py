from helpers.functions import is_app_link


class MediaList:
    @staticmethod
    def List(items: list) -> list | None:
        if items is None or len(items) == 0:
            return None

        result = []
        for n, item in enumerate(items):
            try:
                result.append(MediaList.Item(item))
            except Exception as e:
                print(f"Item {n} failed: {e}")
                continue

        return result if len(result) > 0 else None

    @staticmethod
    def Item(item: str | list) -> list:
        if isinstance(item, str):
            if not is_app_link(item):
                raise Exception("External links are not allowed ")
            return [100, item, None, None, None, None]
        elif isinstance(item, list):
            mediaType, url, desc = item[:3]
            try:
                tag = item[3]
            except Exception:
                tag = None

            if not isinstance(mediaType, int) or not isinstance(url, str):
                raise Exception("Invalid data held in MediaList item")

            if not is_app_link(url):
                raise Exception("External links are not allowed ")

            desc = desc[:255] if isinstance(desc, str) else None
            tag = tag if isinstance(tag, str) else None

            return [mediaType, url, desc, tag, None, None]
        else:
            raise Exception("Invalid item for MediaList!")
