import json

import pytest

import extract_scripts


class TestExtractTextFromScriptPage:
    def test_div_exists(self):
        html = f"""
            <div class="{extract_scripts.SCRIPT_DIV_CLASS}">
                Line1<br>Line2
            </div>
        """

        def fake_fetcher(_):
            return html

        result = extract_scripts.extract_text_from_script_page(script_page_url="",
                                                               fetcher=fake_fetcher)
        assert result == "Line1\nLine2"

    def test_div_not_exists(self):
        html = "<div>Some other content</div>"

        def fake_fetcher(_):
            return html

        result = extract_scripts.extract_text_from_script_page(script_page_url="",
                                                               fetcher=fake_fetcher)
        assert result == ""


class TestExtractNumberOfPages:
    def test_single_page(self):
        html = """
            <a href="/movie_scripts.php?order=a&page=2">2</a>
        """

        def fake_fetcher(_):
            return html

        result = extract_scripts.extract_number_of_pages(letter="a",
                                                         fetcher=fake_fetcher)
        assert result == 2

    def test_multiple_pages(self):
        html = """
            <a href="/movie_scripts.php?order=a&page=1">1</a>
            <a href="/movie_scripts.php?order=a&page=2">2</a>
            <a href="/movie_scripts.php?order=a&page=3">3</a>
        """

        def fake_fetcher(_):
            return html

        result = extract_scripts.extract_number_of_pages(letter="a",
                                                         fetcher=fake_fetcher)
        assert result == 3

    def test_no_links(self):
        html = "<div>No pagination links here</div>"

        def fake_fetcher(_):
            return html

        result = extract_scripts.extract_number_of_pages(letter="a",
                                                         fetcher=fake_fetcher)
        assert result == 1

    def test_non_numeric_page(self):
        html = """
            <a href="/movie_scripts.php?order=a&page=one">one</a>
        """

        def fake_fetcher(_):
            return html

        with pytest.raises(ValueError):
            extract_scripts.extract_number_of_pages(letter="a",
                                                    fetcher=fake_fetcher)

    def test_empty_page(self):
        html = """
            <a href="/movie_scripts.php?order=a&page=">No page</a>
        """

        def fake_fetcher(_):
            return html

        with pytest.raises(ValueError):
            extract_scripts.extract_number_of_pages(letter="a",
                                                    fetcher=fake_fetcher)

    def test_invalid_links(self):
        html = """
            <a href="/scripts.php?order=a&page=2">2</a>
            <a href="/movie_scripts.php?order=a">3</a>
        """

        def fake_fetcher(_):
            return html

        result = extract_scripts.extract_number_of_pages(letter="a",
                                                         fetcher=fake_fetcher)
        assert result == 1


@pytest.fixture
def mocked_s3_bucket(mocker):
    bucket = mocker.Mock()
    mocker.patch("extract_scripts.get_s3_bucket", return_value=bucket)
    return bucket


@pytest.fixture
def mock_s3_bucket_with_side_effect(mocker):
    bucket = mocker.Mock()
    bucket.upload_file.side_effect = Exception("S3 upload failed")
    mocker.patch("extract_scripts.get_s3_bucket", return_value=bucket)
    return bucket


class TestExtractAndStoreScripts:
    def test_single_page(self, mocked_s3_bucket):
        html = """
            <html><body>
                <a href="/movie_script.php?movie=movie1">Movie 1</a>
                <a href="/movie_script.php?movie=movie2">Movie 2</a>
            </body></html>
        """

        script_htmls = {
            f"{extract_scripts.WEBSITE_URL}/movie_script.php?movie=movie1": f"""
                <div class="{extract_scripts.SCRIPT_DIV_CLASS}">
                    Script content for Movie 1
                </div>
            """,
            f"{extract_scripts.WEBSITE_URL}/movie_script.php?movie=movie2": f"""
                <div class="{extract_scripts.SCRIPT_DIV_CLASS}">
                    Script content for Movie 2
                </div>
            """
        }

        def fake_fetcher(url):
            if "movie_script.php" in url:
                return script_htmls[url]
            return html

        written = {}

        def fake_writer(path, content):
            written["path"] = path
            written["content"] = content

        extract_scripts.extract_and_store_scripts(
            "a", fetcher=fake_fetcher, writer=fake_writer
        )

        expected_data = [
            {
                "movie": "Movie 1",
                "script": "Script content for Movie 1".replace("\n", "\\n").strip(),
            },
            {
                "movie": "Movie 2",
                "script": "Script content for Movie 2".replace("\n", "\\n").strip()
            }
        ]

        assert written["path"] == extract_scripts.SCRIPT_FILE_NAME.format(letter="a")
        assert json.loads(written["content"]) == expected_data
        mocked_s3_bucket.upload_file.assert_called_once()

    def test_multiple_pages(self, mocked_s3_bucket):
        page_htmls = {
            1: """
                <html><body>
                    <a href="/movie_script.php?movie=movie1">Movie 1</a>
                    <a href="/movie_scripts.php?order=a&page=2">2</a>
                </body></html>
            """,
            2: """
                <html><body>
                    <a href="/movie_script.php?movie=movie2">Movie 2</a>
                    <a href="/movie_scripts.php?order=a&page=1">1</a>
                </body></html>
            """
        }

        script_htmls = {
            f"{extract_scripts.WEBSITE_URL}/movie_script.php?movie=movie1": f"""
                <div class="{extract_scripts.SCRIPT_DIV_CLASS}">
                    Script content for Movie 1
                </div>
            """,
            f"{extract_scripts.WEBSITE_URL}/movie_script.php?movie=movie2": f"""
                <div class="{extract_scripts.SCRIPT_DIV_CLASS}">
                    Script content for Movie 2
                </div>
            """
        }

        def fake_fetcher(url):
            if "page=1" in url:
                return page_htmls[1]
            elif "page=2" in url:
                return page_htmls[2]
            elif "movie_script.php" in url:
                return script_htmls[url]
            return ""

        written = {}

        def fake_writer(path, content):
            written["path"] = path
            written["content"] = content

        extract_scripts.extract_and_store_scripts(
            "a", fetcher=fake_fetcher, writer=fake_writer
        )

        expected_data = [
            {
                "movie": "Movie 1",
                "script": "Script content for Movie 1".replace("\n", "\\n").strip(),
            },
            {
                "movie": "Movie 2",
                "script": "Script content for Movie 2".replace("\n", "\\n").strip()
            }
        ]

        assert written["path"] == extract_scripts.SCRIPT_FILE_NAME.format(letter="a")
        assert json.loads(written["content"]) == expected_data
        mocked_s3_bucket.upload_file.assert_called_once()

    def test_no_scripts(self, mocked_s3_bucket):
        html = """
            <html><body>
                <p>No scripts available.</p>
            </body></html>
        """

        def fake_fetcher(_):
            return html

        written = {}

        def fake_writer(path, content):
            written["path"] = path
            written["content"] = content

        extract_scripts.extract_and_store_scripts(
            "a", fetcher=fake_fetcher, writer=fake_writer
        )

        assert written["content"] == "[]"
        mocked_s3_bucket.upload_file.assert_called_once()

    def test_no_s3_bucket_env(self, mocker):
        mocker.patch.dict("os.environ", {}, clear=True)
        with pytest.raises(ValueError, match="S3_BUCKET_NAME environment variable is not set."):
            extract_scripts.get_s3_bucket()

    def test_s3_upload_failure(self, mock_s3_bucket_with_side_effect):
        html = """
            <html><body>
                <a href="/movie_script.php?movie=movie1">Movie 1</a>
            </body></html>
        """

        script_html = f"""
            <div class="{extract_scripts.SCRIPT_DIV_CLASS}">
                Script content for Movie 1
            </div>
        """

        def fake_fetcher(url):
            if "movie_script.php" in url:
                return script_html
            return html

        written = {}

        def fake_writer(path, content):
            written["path"] = path
            written["content"] = content

        with pytest.raises(Exception, match="S3 upload failed"):
            extract_scripts.extract_and_store_scripts(
                "a", fetcher=fake_fetcher, writer=fake_writer
            )
