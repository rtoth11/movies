import logging
import os
import re
import requests
from typing import Optional

import psycopg2


def download_pdf(pdf_link: str, download_path: str) -> Optional[str]:
    with requests.get(pdf_link) as response:
        if response.status_code != 200:
            logging.warning(f"Failed to download PDF from {pdf_link}: "
                            f"Status code {response.status_code}.")
            return None
        with open(download_path, "wb") as f:
            f.write(response.content)
    return download_path


def _strip_trailing_asterisks(s: str) -> tuple[str, bool]:
    had_asterisk = bool(re.search(r"\*+\s*$", s))
    cleaned = re.sub(r"\*+\s*$", "", s).rstrip()
    return cleaned, had_asterisk


def clean_lines(lines: list[str]) -> tuple[list[str], bool]:
    cleaned_lines = []
    block_revised = False
    for i, line in enumerate(lines):
        cleaned_line, had_asterisk = _strip_trailing_asterisks(line)
        if had_asterisk or line.strip() == "*":
            block_revised = True
        cleaned_lines.append(cleaned_line)
    return cleaned_lines, block_revised


def remove_useless_lines(lines: list[str]) -> list[str]:
    """
    Remove lines from the list that match:
      - "(CONTINUED)"
      - "(MORE)"
      - "CONTINUED: (<1-999>)"
      - a single number or a single number with a trailing character (like "1." or "1a")
      - contains " REV." OR " REVISED"
    Case-insensitive.
    """
    pattern = re.compile(
        r"^\s*(\((continued|more)\)|continued:\s*\([1-9]\d{0,2}\))\s*$",
        re.IGNORECASE
    )
    return [item for item in lines
            if not pattern.match(item)
            and not item.isdigit()
            and not item[0:-1].isdigit()
            and " REV." not in item
            and " REVISED" not in item]


def create_character_actor_map(script_data: list[dict], cast: list[dict]) -> list[dict]:
    script_characters = set(d["character"] for d in script_data
                            if d["type"] in ("dialogue", "empty_dialogue"))
    cast_map = {c["character"]: {"actor_tmdb_id": c["id"], "actor_name": c["name"]} for c in cast}

    result = []

    for script_character in script_characters:
        script_character_lower = script_character.lower()

        exact_match = None
        character_and_actor = {
            "character": script_character,
            "actor_tmdb_id": None,
            "actor_name": None
        }
        for cast_character, actor in cast_map.items():
            if cast_character.lower() == script_character_lower:
                exact_match = actor
                break

        if exact_match:
            character_and_actor.update(exact_match)
            result.append(character_and_actor)
            continue

        substring_matches = []
        for cast_character, actor in cast_map.items():
            cast_character_lower = cast_character.lower()
            if script_character_lower in cast_character_lower:
                substring_matches.append((cast_character, actor))

        if substring_matches:
            # Pick the cast character with the shortest name
            best_cast_char, best_actor = min(substring_matches, key=lambda x: len(x[0]))
            character_and_actor.update(best_actor)
            result.append(character_and_actor)
        else:
            logging.debug(f"No actor found for character {script_character}.")
            result.append(character_and_actor)

    return result


def get_already_stored_movies() -> set[int]:
    pg_conn = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT")),
        dbname=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )

    try:
        with pg_conn.cursor() as cursor:
            cursor.execute("SELECT tmdb_id FROM models.silver_movies;")
            rows = cursor.fetchall()
            return {row[0] for row in rows}
    finally:
        pg_conn.close()
