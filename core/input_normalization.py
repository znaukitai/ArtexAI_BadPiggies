"""Normalize room codes without transliterating ordinary Russian prose."""
import re

GREETING = "Привет! Помогу с дедлайнами, планом недели, GitHub и аудиториями — например, «Что горит на неделе?» или «Где C1.226?»"


def is_greeting(value: str | None) -> bool:
    return str(value or "").strip().casefold().strip("!?. ") in {
        "привет", "здравствуйте", "салем", "hi", "hello", "hey",
    }


def normalize_room_query(value: str) -> str:
    def replace(match: re.Match) -> str:
        code = match.group(0).translate(str.maketrans("сСкКрР", "cCkKpP"))
        return re.sub(r"[\s.-]+", ".", code).upper()
    return re.sub(r"(?<!\w)[cс]1[\s.-]+(?:[1-3][\s.-]+)?\d{3}[kкlрp]?(?!\w)", replace, value, flags=re.I)


def normalize_api_key(value: str | None) -> str:
    return str(value or "").strip(" \t\r\n\"'")
