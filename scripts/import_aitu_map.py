"""Import room and facility index from the AITU map repository."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = "028869ba9f6b03627d7bef64511491101adf2ace"
BASE = f"https://raw.githubusercontent.com/Yuujiso/aitumap/{REVISION}/src/shared/ui/separate"
MAP_URL = "https://yuujiso.github.io/aitumap/"
ROOM_RE = re.compile(r"(?<![A-Za-z0-9])C1\.([1-3])\.(\d{3})([KLP]?)(?![A-Za-z0-9])")
SHORT_ROOM_RE = re.compile(r"(?<![A-Za-z0-9.])\d\.(\d{3})([KLP]?)(?![A-Za-z0-9])")
FILES = {(block, floor): f"C1_{block}_{floor}.jsx" for block in range(1, 4) for floor in range(1, 4)}


def load_room_index() -> dict:
    rooms: dict[str, dict] = {}
    facilities: dict[tuple[str, int, str], dict] = {}
    for (current_block, floor), filename in FILES.items():
        request = urllib.request.Request(f"{BASE}/{filename}", headers={"User-Agent": "CampusPulse-Map-Importer/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            source = response.read().decode("utf-8")
        groups = re.findall(r'data-name="([^"]*)"', source)
        for group in groups:
            aliases = [part.strip() for part in group.split("|") if part.strip()]
            found_room = False
            matches = list(ROOM_RE.finditer(group))
            remaining = ROOM_RE.sub("", group)
            matches.extend(SHORT_ROOM_RE.finditer(remaining))
            for match in matches:
                if match.re is ROOM_RE:
                    block, room, suffix = match.groups()
                else:
                    room, suffix = match.groups()
                    block = current_block
                code = f"C1.{block}.{room}{suffix}"
                record = rooms.setdefault(code, {
                    "code": code,
                    "name": f"Помещение {code}",
                    "block": f"C1.{block}",
                    "floor": floor,
                    "room_number": f"{room}{suffix}",
                    "kind": "room",
                    "aliases": [],
                    "map_url": MAP_URL,
                    "source": "demo",
                })
                for alias in aliases:
                    if alias != code and alias not in record["aliases"]:
                        record["aliases"].append(alias)
                found_room = True
            if not found_room:
                facility_aliases = []
                for part in aliases:
                    normalized = re.sub(r"^C1\.[1-3]\.", "", part, flags=re.IGNORECASE)
                    if normalized and normalized not in facility_aliases:
                        facility_aliases.append(normalized)
                label = "|".join(facility_aliases)
                if label:
                    key = (current_block, floor, label.casefold())
                    facilities.setdefault(key, {
                        "code": f"facility:{current_block}:F{floor}:{len(facilities)+1}",
                        "name": label.split("|", 1)[0],
                        "block": f"C1.{current_block}",
                        "floor": floor,
                        "room_number": None,
                        "kind": "facility",
                        "aliases": facility_aliases,
                        "map_url": MAP_URL,
                        "source": "demo",
                    })
    places = [*rooms.values(), *facilities.values()]
    return {
        "institution": "Astana IT University",
        "dataset": "Interactive map room and facility labels",
        "source": "https://github.com/Yuujiso/aitumap",
        "source_revision": REVISION,
        "map_url": MAP_URL,
        "license": "MIT",
        "coverage": "Blocks C1.1, C1.2 and C1.3, floors 1-3.",
        "places": sorted(places, key=lambda item: (item["block"], item["floor"], item["code"])),
    }


if __name__ == "__main__":
    payload = load_room_index()
    output = ROOT / "data" / "aitu_map_rooms.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['places'])} map labels to {output}")
