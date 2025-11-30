import io
import json
import logging
import os
from pathlib import Path
import re
import requests

from bs4 import BeautifulSoup
from databricks.sdk import WorkspaceClient
import pymupdf
import tmdbsimple as tmdb

from get_scripts_request import cookies, headers, json_data
from script_verification import write_blocks_to_txt
import utils

GENRES = ["action", "adventure"]

SCRIPTS_WEBSITE = "https://www.scriptslug.com"
SCRIPTS_API_LINK = "https://www.scriptslug.com/gql"

VOLUME_FILE_PATH = f"{os.getenv('DATABRICKS_MOVIE_DATA_VOLUME_PATH')}/{{genre}}_movies.json"
SCRIPT_PDF_PATH = os.path.join("/tmp", "{movie}.pdf")

CHARACTER_LINE_RE = re.compile(r"^([A-Z0-9 '.-]+?)(?:\s*\(([^)]+)\))*$")
SCENE_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.)")
ONE_OR_MORE_PARENTHESIS = r"\(([^)]+)\)"

tmdb.API_KEY = os.getenv("TMDB_API_KEY")
tmdb_search = tmdb.Search()

checked_script_pages = set()


def _add_movie_data(movie_title: str, movie_year: str, script_data: list[dict]) -> dict:
    response = tmdb_search.movie(query=movie_title, year=movie_year)
    candidate_movies = [movie for movie in response["results"] if movie["title"] == movie_title]

    if len(candidate_movies) == 0:
        logging.warning(
            f"The {movie_title} ({movie_year}) movie was not found. Skipping it.")
        return {}
    if len(candidate_movies) > 1:
        logging.warning(
            f"Multiple results for the {movie_title} ({movie_year}) movie. Skipping it.")
        return {}

    movie = tmdb.Movies(candidate_movies[0]["id"])
    cast = movie.credits()["cast"]

    return {
        "tmdb_id": candidate_movies[0]["id"],
        "title": movie_title,
        "year": movie_year,
        "script": script_data,
        "character_to_actor": utils.create_character_actor_map(script_data, cast)
    }


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


def _extract_script_links(genre: str) -> list[tuple]:
    logging.info("Extracting script links.")

    script_links = []

    headers["referer"] = headers["referer"].format(genre=genre)
    response = requests.post(SCRIPTS_API_LINK,
                             cookies=cookies,
                             headers=headers,
                             json=json_data)
    script_page_links = [f"{SCRIPTS_WEBSITE}/{entry['uri']}"
                         for entry in response.json()["data"]["scriptsEntries"]]

    for script_page_link in script_page_links:
        # The same movie can appear in multiple genres
        if script_page_link in checked_script_pages:
            continue
        checked_script_pages.add(script_page_link)

        logging.debug(f"Script link: {script_page_link}")

        with requests.get(script_page_link) as script_page_response:
            soup = BeautifulSoup(script_page_response.content, "html.parser")
            link_element = soup.find("a", href=re.compile("live/pdf/scripts"))
            title_element = soup.find(
                "span", class_="text-3xl leading-normal md:text-4xl lg:text-5xl lg:leading-normal")
            type_and_year_element = soup.find(
                "p", class_="font-semibold text-slate-500 font-slab text-lg")

            if link_element is not None:
                script_links.append((
                    title_element.text.strip(),
                    type_and_year_element.text.split("-")[1].strip(),
                    link_element["href"]
                ))
            else:
                logging.warning(f"No script link found on page: {script_page_link}")

        if len(script_links) > 20:
            break # TODO: remove

    return script_links


def _extract_and_store_movie_data(genre: str, workspace_client: WorkspaceClient):
    all_movies = []

    logging.info(f"Extracting movie data for genre '{genre}'.")

    script_links = _extract_script_links(genre)

    logging.info(f"Found {len(script_links)} scripts for genre '{genre}'.")

    for movie_title, movie_year, script_link in script_links:
        logging.debug(f"Extracting script from {script_link}.")

        download_path = SCRIPT_PDF_PATH.format(movie=script_link.split(".pdf")[0].split("/")[-1])
        pdf_path = utils.download_pdf(script_link, download_path)

        script_data = _extract_script_from_pdf(pdf_path)
        movie_data = _add_movie_data(movie_title, movie_year, script_data)
        if movie_data != {}:
            all_movies.append(movie_data)

    json_bytes = json.dumps(all_movies, indent=2).encode("utf-8")
    binary_stream = io.BytesIO(json_bytes)
    workspace_client.files.upload(VOLUME_FILE_PATH.format(genre=genre),
                                  binary_stream,
                                  overwrite=True)

def handler(event, context):
    logging.getLogger().setLevel(logging.INFO)
    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_token = os.getenv("DATABRICKS_TOKEN")
    if databricks_host is not None:
        workspace_client = WorkspaceClient(host=databricks_host, token=databricks_token)
    else:
        workspace_client = WorkspaceClient()
    for genre in GENRES:
        _extract_and_store_movie_data(genre, workspace_client)


if __name__ == "__main__":
    handler(None, None)
