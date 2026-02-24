import io
import json
import logging
import os
from pathlib import Path
import re
import requests
from requests.adapters import HTTPAdapter
from typing import Optional
from urllib3.util.retry import Retry

from bs4 import BeautifulSoup
from databricks.sdk import WorkspaceClient
import pymupdf
import tmdbsimple as tmdb

from get_scripts_request import json_data
from script_verification import write_blocks_to_txt
import utils

SELECTED_GENRES = os.getenv("GENRES")
ALL_GENRES = [
    ("action", 10540),
    ("adventure", 10541),
    ("animation", 10546),
    ("biography", 10535),
    ("comedy", 10532),
    ("crime", 10542),
    ("drama", 10533),
    ("family", 10547),
    ("fantasy", 10543),
    ("film-noir", 10550),
    ("history", 10536),
    ("holiday", 10554),
    ("horror", 10538),
    ("music", 10549),
    ("musical", 10552),
    ("mystery", 10544),
    ("romance", 10534),
    ("science-fiction", 10539),
    ("short", 10555),
    ("sport", 10537),
    ("superhero", 10553),
    ("thriller", 10545),
    ("war", 10548),
    ("western", 10551)
]
if SELECTED_GENRES is not None:
    GENRES = [genre for genre in ALL_GENRES if genre[0] in SELECTED_GENRES.split(",")]
else:
    GENRES = ALL_GENRES

NUMBER_OF_MOVIES = os.getenv("NUMBER_OF_MOVIES")

SCRIPTS_WEBSITE = "https://www.scriptslug.com"
SCRIPTS_API_LINK = "https://www.scriptslug.com/gql"
REFERER = "https://www.scriptslug.com/scripts/genre/{genre}?pg=50"

VOLUME_PATH = os.getenv("DATABRICKS_MOVIE_DATA_VOLUME_PATH")
VOLUME_FILE_PATH = f"{VOLUME_PATH}{{genre}}_movies.json"
SCRIPT_PDF_PATH = os.path.join("/tmp", "{movie}.pdf")

CHARACTER_LINE_RE = re.compile(r"^([A-Z0-9 '.-]+?)(?:\s*\(([^)]+)\))*$")
SCENE_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.)")
ONE_OR_MORE_PARENTHESIS = r"\(([^)]+)\)"

tmdb.API_KEY = os.getenv("TMDB_API_KEY")
tmdb_search = tmdb.Search()

checked_script_pages = set()

session = requests.Session()

retries = Retry(
    total=1,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retries)

session.mount("https://", adapter)
session.mount("http://", adapter)

tmdb.REQUESTS_SESSION = session


def _process_dialogue_lines(lines: list[str]) -> tuple[list[str], str, list[list[str]], list[str]]:
    dialogue_text = []
    parenthetical = ""

    # Normally, the lines form 1 dialogue block. However, if multiple parentheticals appear in the
    # lines, the dialogues will be stored as separate blocks with their respective parenthetical(s).
    # When a new parenthetical starts, the previous ones are also stored along the new one.
    extra_dialogue_texts = []
    extra_parentheticals = []

    in_parenthetical = False
    parenthetical_lines = []

    for line in lines:
        stripped_line = line.strip()

        # Start a parenthetical
        if not in_parenthetical and stripped_line.startswith("("):
            if dialogue_text:
                extra_dialogue_texts.append(dialogue_text)
                extra_parentheticals.append(parenthetical)
                dialogue_text = []

            in_parenthetical = True
            parenthetical_lines = [stripped_line.lstrip("(").rstrip(")")]

            if stripped_line.endswith(")"):
                in_parenthetical = False
                current = " ".join(parenthetical_lines)
                parenthetical = f"{parenthetical}; {current}" if parenthetical else current
            continue

        # Inside multi-line parenthetical
        if in_parenthetical:
            cleaned = stripped_line.rstrip(")")
            parenthetical_lines.append(cleaned)

            if stripped_line.endswith(")"):
                in_parenthetical = False
                current = " ".join(parenthetical_lines)
                parenthetical = f"{parenthetical}; {current}" if parenthetical else current
            continue

        # Normal dialogue
        if stripped_line:
            dialogue_text.append(stripped_line)

    return dialogue_text, parenthetical, extra_dialogue_texts, extra_parentheticals


def _extract_blocks_from_page(pdf_page: pymupdf.Page, current_index: int) -> tuple[list[dict], int]:
    blocks = pdf_page.get_text_blocks()
    page_width = pdf_page.rect.width
    center_x = page_width / 2

    extracted_blocks = []
    index = current_index

    character_started = False
    character, suffix = None, None

    for block in blocks:
        x0, y0, x1, y1, text, block_number, _ = block
        block_width = x1 - x0
        block_center = (x0 + x1) / 2

        text = text.strip()
        if not text:
            continue

        split_lines = text.splitlines()
        filtered_lines = utils.remove_useless_lines(split_lines)
        if len(filtered_lines) == 0:
            continue
        lines, block_revised = utils.clean_lines(filtered_lines)
        first = lines[0].strip()

        narrow = block_width < page_width * 0.5
        centered = abs(block_center - center_x) < page_width * 0.18
        wide = block_width > page_width * 0.5

        # SCENE HEADING
        if SCENE_RE.match(first) and first.isupper():
            extracted_blocks.append(
                {
                    "index": index,
                    "type": "scene",
                    "content": first
                }
            )
            index += 1
            continue

        # CHARACTER LINE (dialogue)
        character_match = CHARACTER_LINE_RE.match(first)

        if (narrow or block_revised) \
                and (centered or block_revised) \
                and (character_match or character_started):

            if character_match:
                character = character_match.group(1)
                suffix = ", ".join(re.findall(ONE_OR_MORE_PARENTHESIS, first))
                suffix = suffix or ""
                if len(lines) == 1:
                    character_started = True
                    continue

            dialogue_text, parenthetical, extra_dialogue_texts, extra_parentheticals = \
                _process_dialogue_lines(lines if character_started else lines[1:])

            for i in range(len(extra_dialogue_texts)):
                extracted_blocks.append(
                    {
                        "index": index,
                        "type": "dialogue",
                        "character": character,
                        "dialogue": " ".join(extra_dialogue_texts[i]),
                        "suffix": suffix,
                        "parentheticals": extra_parentheticals[i]
                    }
                )
                index += 1

            if character_started:
                character_started = False

            if len(dialogue_text) == 0:
                extracted_blocks.append(
                    {
                        "index": index,
                        "type": "empty_dialogue",
                        "character": character
                    }
                )
                index += 1
                continue

            extracted_blocks.append(
                {
                    "index": index,
                    "type": "dialogue",
                    "character": character,
                    "dialogue": " ".join(dialogue_text),
                    "suffix": suffix,
                    "parentheticals": parenthetical
                }
            )

            index += 1
            continue

        # DESCRIPTION / ACTION
        # Wide or strongly left-aligned text that doesn't contain useless lines
        if (wide or x0 < page_width * 0.20) \
                and not first.isupper() \
                and len(split_lines) == len(filtered_lines):
            extracted_blocks.append(
                {
                    "index": index,
                    "type": "description",
                    "content": text
                }
            )
            index += 1
            continue

        # UNKNOWN
        extracted_blocks.append(
            {
                "index": index,
                "type": "unknown",
                "content": text
            }
        )
        index += 1

    return extracted_blocks, index


def _extract_script_from_pdf(pdf_path: str) -> list[dict]:
    pdf_document = pymupdf.open(pdf_path)
    number_of_pages = pdf_document.page_count
    index = 1
    blocks = []
    # First page is skipped (it's usually the cover)
    for page in range(1, number_of_pages):
        new_blocks, index = _extract_blocks_from_page(pdf_document[page], index)
        blocks += new_blocks
    # write_blocks_to_txt(blocks, Path(pdf_document.name).stem)
    return blocks


def _should_process_movie(movie_title: str,
                          movie_year: str,
                          already_stored_movies: set[tuple[str, str]]) -> Optional[int]:
    if (movie_title, movie_year) in already_stored_movies:
        logging.debug(f"The {movie_title} ({movie_year}) movie is already stored. Skipping it.")
        return None

    response = tmdb_search.movie(query=movie_title, year=movie_year)
    candidate_movies = [
        movie for movie in response["results"]
        if (movie["title"].replace(":", "").replace("-", "")
            == movie_title.replace(":", "").replace("-", ""))
    ]

    if len(candidate_movies) == 0:
        logging.debug(
            f"The {movie_title} ({movie_year}) movie was not found. Skipping it.")
        return None

    if len(candidate_movies) > 1:
        logging.debug(
            f"Multiple candidates for the {movie_title} ({movie_year}) movie. Skipping it.")
        return None

    return candidate_movies[0]["id"]


def _extract_script_links(genre: tuple[str, int], already_stored_movies: set[tuple[str, str]]) \
        -> list[tuple[int, str, str, str]]:
    logging.info("Extracting script links.")

    genre_name, genre_id = genre
    json_data["variables"]["relationId"] = genre_id
    script_links = []

    response = session.post(
        SCRIPTS_API_LINK,
        headers={
            "accept": "*/*",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0",
            "origin": SCRIPTS_WEBSITE,
            "referer": REFERER.format(genre=genre_name)
        },
        json=json_data
    )
    response.raise_for_status()
    entries = response.json()["data"]["scriptsEntries"]

    for entry in entries:
        if "scriptTitle" not in entry:
            if "title" in entry:
                logging.debug(f"{entry['title']} is not a movie. Skipping it.")
            else:
                logging.debug(f"Entry without title found: {entry}. Skipping it.")
            continue

        movie_title = entry["scriptTitle"]
        movie_year = entry["year"]
        script_page_link = f"{SCRIPTS_WEBSITE}/{entry['uri']}"

        # The same movie can appear in multiple genres
        if script_page_link in checked_script_pages:
            continue
        checked_script_pages.add(script_page_link)

        movie_tmdb_id = _should_process_movie(movie_title, movie_year, already_stored_movies)
        if movie_tmdb_id is None:
            continue

        script_page_response = session.get(script_page_link)
        script_page_response.raise_for_status()
        soup = BeautifulSoup(script_page_response.content, "html.parser")
        link_element = soup.find("a", href=re.compile("live/pdf/scripts"))

        if link_element is not None:
            script_links.append((
                movie_tmdb_id,
                movie_title,
                movie_year,
                link_element["href"]
            ))
        else:
            logging.warning(f"No script link found on page: {script_page_link}.")

        if NUMBER_OF_MOVIES is not None and len(script_links) > int(NUMBER_OF_MOVIES):
            break

    return script_links


def _extract_and_store_movie_data(genre: tuple[str, int],
                                  workspace_client: WorkspaceClient,
                                  already_stored_movies: set[tuple[str, str]]):
    all_movies = []
    i = 1
    genre_name = genre[0]

    logging.info(f"Extracting movie data for genre '{genre_name}'.")

    script_links = _extract_script_links(genre, already_stored_movies)

    logging.info(f"Found {len(script_links)} scripts for genre '{genre_name}'.")

    for movie_tmdb_id, movie_title, movie_year, script_link in script_links:
        logging.info(f"Extracting script from {i}. link: {script_link}.")

        download_path = SCRIPT_PDF_PATH.format(movie=script_link.split(".pdf")[0].split("/")[-1])
        pdf_path = utils.download_pdf(script_link, download_path, session)

        script_data = _extract_script_from_pdf(pdf_path)
        movie = tmdb.Movies(movie_tmdb_id)
        cast = movie.credits()["cast"]
        movie_data = {
            "tmdb_id": movie_tmdb_id,
            "title": movie_title,
            "year": movie_year,
            "script": script_data,
            "character_to_actor": utils.create_character_actor_map(script_data, cast)
        }

        all_movies.append(movie_data)
        already_stored_movies.add((movie_title, movie_year))
        i += 1

    if len(all_movies) == 0:
        logging.info(f"No new movie data extracted for genre '{genre_name}'.")
        return

    logging.info("Uploading extracted movie data to Databricks workspace.")

    all_movies = utils.remove_null_bytes(all_movies)
    json_bytes = json.dumps(all_movies, indent=2).encode("utf-8")
    binary_stream = io.BytesIO(json_bytes)
    workspace_client.files.upload(VOLUME_FILE_PATH.format(genre=genre_name),
                                  binary_stream,
                                  overwrite=True)

    logging.info("Movie data upload complete.")


def main():
    logging.getLogger().setLevel(logging.INFO)

    logging.info(f"Selected genres: {SELECTED_GENRES}")
    logging.info(f"Number of movies per genre: {NUMBER_OF_MOVIES}")

    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_token = os.getenv("DATABRICKS_TOKEN")

    if databricks_host is not None:
        workspace_client = WorkspaceClient(host=databricks_host, token=databricks_token)
    else:
        workspace_client = WorkspaceClient()

    already_stored_movies = utils.get_already_stored_movies()

    for genre in GENRES:
        _extract_and_store_movie_data(genre, workspace_client, already_stored_movies)


if __name__ == "__main__":
    main()
