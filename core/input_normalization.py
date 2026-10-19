"""Normalize room codes without transliterating ordinary Russian prose."""
import re

def normalize_room_query(value: str) -> str:
    def replace(match: re.Match) -> str:
        code = match.group(0).translate(str.maketrans("сСкКрР", "cCkKpP"))
        return re.sub(r"[\s.-]+", ".", code).upper()
    return re.sub(r"(?<!\w)[cс]1[\s.-]+(?:[1-3][\s.-]+)?\d{3}[kкlрp]?(?!\w)", replace, value, flags=re.I)


def normalize_api_key(value: str | None) -> str:
    return str(value or "").strip(" \t\r\n\"'")
