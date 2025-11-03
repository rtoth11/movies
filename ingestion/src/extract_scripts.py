import json
import logging
import os
import urllib.request

import boto3
from bs4 import BeautifulSoup

WEBSITE_URL = "https://www.springfieldspringfield.co.uk"
SCRIPTS_URL = \
    "https://www.springfieldspringfield.co.uk/movie_scripts.php?order={letter}&page={page}"
SCRIPT_DIV_CLASS = "scrolling-script-container"
MOVIE_SCRIPTS_LINK = "movie_scripts.php"
SCRIPT_FILE_NAME = "/tmp/movie_scripts_{letter}.json"
LETTERS = ["0"] + [chr(i) for i in range(ord("A"), ord("Z") + 1)]


def fetch_url(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def write_file(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)


def extract_text_from_script_page(script_page_url: str, fetcher=fetch_url) -> str:
    html_page = fetcher(script_page_url)
    soup = BeautifulSoup(html_page, "html.parser")
    script_div = soup.find("div", class_=SCRIPT_DIV_CLASS)
    if script_div is not None:
        return script_div.get_text(separator="\n").strip()
    return ""


def extract_number_of_pages(letter: str, fetcher=fetch_url) -> int:
    html_page = fetcher(SCRIPTS_URL.format(letter=letter, page=1))
    soup = BeautifulSoup(html_page, "html.parser")
    max_page = 1
    for link in soup.find_all("a"):
        link_href = link.get("href", "")
        if MOVIE_SCRIPTS_LINK in link_href and "page=" in link_href:
            page_in_link = int(link.get("href").split("page=")[-1])
            if page_in_link > max_page:
                max_page = page_in_link
    return max_page


def get_s3_bucket():
    s3_bucket_name = os.getenv("S3_BUCKET_NAME")
    if s3_bucket_name is None:
        raise ValueError("S3_BUCKET_NAME environment variable is not set.")
    s3 = boto3.resource("s3")
    return s3.Bucket(s3_bucket_name)


def extract_and_store_scripts(letter: str, fetcher=fetch_url, writer=write_file):
    s3_bucket = get_s3_bucket()
    number_of_pages = extract_number_of_pages(letter, fetcher)
    file_name = SCRIPT_FILE_NAME.format(letter=letter)
    scripts_data = []

    logging.info(f"Extracting scripts for letter {letter} with {number_of_pages} page(s).")

    for page in range(1, number_of_pages + 1):
        html_page = fetcher(SCRIPTS_URL.format(letter=letter, page=page))
        soup = BeautifulSoup(html_page, "html.parser")
        script_links = [
            link
            for link in soup.find_all("a")
            if "/movie_script.php?movie=" in link.get("href", "")
        ]

        logging.debug(f"Found {len(script_links)} scripts on page {page} for letter {letter}.")

        for script_link in script_links:
            full_script_url = WEBSITE_URL + script_link.get("href")
            script_text = extract_text_from_script_page(full_script_url, fetcher=fetcher)
            movie_name = script_link.get_text().strip()
            scripts_data.append({"movie": movie_name, "script": script_text})

    writer(file_name, json.dumps(scripts_data, indent=2))
    s3_bucket.upload_file(file_name, f"movie_scripts_{letter}.json")


def handler(event, context):
    logging.getLogger().setLevel(logging.DEBUG)
    for letter in LETTERS:
        extract_and_store_scripts(letter)


if __name__ == "__main__":
    handler(None, None)
