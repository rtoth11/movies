import json
from unittest.mock import Mock, MagicMock

from extract_movie_data import (
    _add_movie_data,
    _process_dialogue_lines,
    _extract_blocks_from_page,
    _extract_script_from_pdf,
    _should_process_movie,
    _extract_script_links,
    _extract_and_store_movie_data,
    tmdb_search,
    checked_script_pages,
    SCRIPT_PDF_PATH,
    VOLUME_FILE_PATH
)
import extract_movie_data


def test__add_movie_data_success(mocker):
    mocker.patch.object(
        tmdb_search,
        "movie",
        return_value={"results": [{"title": "Movie", "id": 123}]}
    )

    mock_movie = Mock()
    mock_movie.credits.return_value = {
        "cast": [
            {"id": 10, "name": "Actor", "character": "Hero"}
        ]
    }

    mocker.patch("extract_movie_data.tmdb.Movies", return_value=mock_movie)
    mocker.patch("extract_movie_data.utils.create_character_actor_map",
                 return_value=[{"test": "ok"}])

    script_data = [{"dummy": True}]
    result = _add_movie_data("Movie", "2020", script_data)

    assert result == {
        "tmdb_id": 123,
        "title": "Movie",
        "year": "2020",
        "script": script_data,
        "character_to_actor": [{"test": "ok"}]
    }


def test__process_dialogue_lines_basic():
    lines = [
        "Hello there.",
        "How are you?"
    ]
    dialogue, parenthetical, extra_dialogues, extra_parentheticals = _process_dialogue_lines(lines)

    assert dialogue == ["Hello there.", "How are you?"]
    assert parenthetical == ""
    assert extra_dialogues == []
    assert extra_parentheticals == []


def test__process_dialogue_lines_with_parentheticals():
    lines = [
        "(whispering)",
        "Hello.",
        "(angry)",
        "Leave now.",
    ]

    dialogue, parenthetical, extras, extra_parentheticals = _process_dialogue_lines(lines)

    assert dialogue == ["Leave now."]
    assert parenthetical == "whispering; angry"
    assert extras == [["Hello."]]
    assert extra_parentheticals == ["whispering"]


def test__process_dialogue_lines_with_multiline_parentheticals():
    lines = [
        "(whispering",
        "softly)",
        "Hello there.",
        "(angry",
        "loudly)",
        "Get out!"
    ]

    dialogue, parenthetical, extra_dialogues, extra_parentheticals = _process_dialogue_lines(lines)

    assert dialogue == ["Get out!"]
    assert parenthetical == "whispering softly; angry loudly"
    assert extra_dialogues == [["Hello there."]]
    assert extra_parentheticals == ["whispering softly"]


def make_block(x0, y0, x1, y1, text):
    return x0, y0, x1, y1, text, 0, None


def test__extract_blocks_from_page_scene(mocker):
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(0, 0, 900, 50, "INT. HOUSE - DAY")
    ]

    mocker.patch("extract_movie_data.utils.remove_useless_lines", return_value=["INT. HOUSE - DAY"])
    mocker.patch("extract_movie_data.utils.clean_lines", return_value=(["INT. HOUSE - DAY"], False))

    blocks, next_index = _extract_blocks_from_page(page, 1)

    assert blocks == [
        {
            "index": 1,
            "type": "scene",
            "content": "INT. HOUSE - DAY"
        }
    ]
    assert next_index == 2


def test__extract_blocks_from_page_description(mocker):
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(0, 0, 900, 50, "A quiet room.")
    ]

    mocker.patch("extract_movie_data.utils.remove_useless_lines", return_value=["A quiet room."])
    mocker.patch("extract_movie_data.utils.clean_lines", return_value=(["A quiet room."], False))

    blocks, _ = _extract_blocks_from_page(page, 1)

    assert blocks == [
        {
            "index": 1,
            "type": "description",
            "content": "A quiet room."
        }
    ]


def test__extract_blocks_from_page_dialogue(mocker):
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(400, 60, 600, 100, "JOHN\n(whispering)\nHello there. How are you?")
    ]

    mocker.patch(
        "extract_movie_data.utils.remove_useless_lines",
        return_value=["JOHN", "(whispering)", "Hello there. How are you?"]
    )
    mocker.patch(
        "extract_movie_data.utils.clean_lines",
        return_value=(["JOHN", "(whispering)", "Hello there. How are you?"], False)
    )

    blocks, _ = _extract_blocks_from_page(page, 1)

    assert blocks == [
        {
            "index": 1,
             "type": "dialogue",
             "character": "JOHN",
             "dialogue": "Hello there. How are you?",
             "suffix": "",
             "parentheticals": "whispering"
        }
    ]


def test__extract_blocks_from_page_empty_block():
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(0, 0, 10, 10, " "),
        make_block(0, 10, 10, 20, "(CONTINUED)")
    ]

    blocks, _ = _extract_blocks_from_page(page, 1)

    assert blocks == []


def test__extract_blocks_from_page_useless_block():
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(0, 0, 10, 10, "(CONTINUED)")
    ]

    blocks, _ = _extract_blocks_from_page(page, 1)

    assert blocks == []


def test__extract_blocks_from_page_dialogue_in_next_block(mocker):
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(400, 60, 600, 100, "JOHN"),
        make_block(400, 110, 600, 150, "(whispering)\nHello there. How are you?")
    ]

    # side_effect to return different values on consecutive calls
    mocker.patch(
        "extract_movie_data.utils.remove_useless_lines",
        side_effect=[
            ["JOHN"],
            ["(whispering)", "Hello there. How are you?"]
        ]
    )
    mocker.patch(
        "extract_movie_data.utils.clean_lines",
        side_effect=[
            (["JOHN"], False),
            (["(whispering)", "Hello there. How are you?"], False)
        ]
    )

    blocks, _ = _extract_blocks_from_page(page, 1)

    assert blocks == [
        {
            "index": 1,
             "type": "dialogue",
             "character": "JOHN",
             "dialogue": "Hello there. How are you?",
             "suffix": "",
             "parentheticals": "whispering"
        }
    ]


def test__extract_blocks_from_page_extra_dialogues(mocker):
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(400, 60, 600, 100,
                   "JOHN\n(whispering)\nHello.\nHow are you?\n(angry)\nLeave now.")
    ]

    mocker.patch(
        "extract_movie_data.utils.remove_useless_lines",
        return_value=["JOHN", "(whispering)", "Hello.", "How are you?", "(angry)", "Leave now."]
    )
    mocker.patch(
        "extract_movie_data.utils.clean_lines",
        return_value=(
            ["JOHN", "(whispering)", "Hello.", "How are you?", "(angry)", "Leave now."],
            False)
    )

    blocks, _ = _extract_blocks_from_page(page, 1)

    assert blocks == [
        {
            "index": 1,
             "type": "dialogue",
             "character": "JOHN",
             "dialogue": "Hello. How are you?",
             "suffix": "",
             "parentheticals": "whispering"},
        {
            "index": 2,
             "type": "dialogue",
             "character": "JOHN",
             "dialogue": "Leave now.",
             "suffix": "",
             "parentheticals": "whispering; angry"
        }
    ]


def test__extract_blocks_from_page_empty_dialogue_block(mocker):
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(400, 60, 600, 100, "JOHN\n(whispering)\n")
    ]

    mocker.patch(
        "extract_movie_data.utils.remove_useless_lines",
        return_value=["JOHN", "(whispering)"]
    )
    mocker.patch(
        "extract_movie_data.utils.clean_lines",
        return_value=(["JOHN", "(whispering)"], False)
    )

    blocks, _ = _extract_blocks_from_page(page, 1)

    assert blocks == [
        {
            "index": 1,
            "type": "empty_dialogue",
            "character": "JOHN"
        }
    ]


def test__extract_blocks_from_page_unknown_blocks(mocker):
    page = Mock()
    page.rect.width = 1000
    page.get_text_blocks.return_value = [
        make_block(700, 0, 900, 50, "Some random text that doesn't fit any category."),
        make_block(700, 0, 900, 50, "ALL CAPS LINE THAT IS NOT A SCENE.")
    ]

    mocker.patch(
        "extract_movie_data.utils.remove_useless_lines",
        return_value=["Some random text that doesn't fit any category."]
    )
    mocker.patch(
        "extract_movie_data.utils.clean_lines",
        return_value=(["Some random text that doesn't fit any category."], False)
    )

    blocks, _ = _extract_blocks_from_page(page, 1)

    assert blocks == [
        {
            "index": 1,
            "type": "unknown",
            "content": "Some random text that doesn't fit any category."
        },
        {
            "index": 2,
            "type": "unknown",
            "content": "ALL CAPS LINE THAT IS NOT A SCENE."
        }
    ]


def test__extract_script_from_pdf(mocker):
    fake_doc = MagicMock()
    fake_doc.page_count = 3
    fake_doc.__getitem__.side_effect = lambda i: f"page-{i}"

    mock_extract = mocker.patch(
        "extract_movie_data._extract_blocks_from_page",
        side_effect=[(["block1"], 2), (["block2"], 3)]
    )

    mocker.patch("extract_movie_data.pymupdf.open", return_value=fake_doc)

    result = _extract_script_from_pdf("fake.pdf")

    assert result == ["block1", "block2"]
    assert mock_extract.call_count == 2


def test__should_process_movie_no_results(mocker):
    mocker.patch.object(
        tmdb_search,
        "movie",
        return_value={"results": []}
    )

    result = _should_process_movie("FakeMovie", "2020", set())
    assert result == False


def test__should_process_movie_multiple_results(mocker):
    mocker.patch.object(
        tmdb_search,
        "movie",
        return_value={"results": [{"title": "Movie"}, {"title": "Movie"}]}
    )

    result = _should_process_movie("Movie", "2020", set())
    assert result == False


def test__should_process_movie_movie_already_stored(mocker):
    mocker.patch.object(
        tmdb_search,
        "movie",
        return_value={"results": [{"title": "Movie", "id": 123}]}
    )

    result = _should_process_movie("Movie", "2020", {123})
    assert result == False


def test__should_process_movie_success(mocker):
    mocker.patch.object(
        tmdb_search,
        "movie",
        return_value={"results": [{"title": "Movie", "id": 123}]}
    )

    result = _should_process_movie("Movie", "2020", set())
    assert result == True


def test__extract_script_links(mocker):
    # mock GraphQL response
    mock_post = mocker.patch("extract_movie_data.requests.post")
    mock_post.return_value.json.return_value = {
        "data": {
            "scriptsEntries": [
                {"uri": "movie-1"},
                {"uri": "movie-2"}
            ]
        }
    }

    # mock script page fetch
    def fake_get(url):
        fake_resp = Mock()
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None

        fake_resp.content = b"""
            <a href="https://some-website.com/live/pdf/scripts/m1.pdf">PDF</a>
            <span class="text-3xl leading-normal md:text-4xl lg:text-5xl lg:leading-normal">Movie 1</span>
            <p class="font-semibold text-slate-500 font-slab text-lg">Film - 2020</p>
        """
        return fake_resp

    mocker.patch("extract_movie_data.requests.get", side_effect=fake_get)

    checked_script_pages.clear()

    result = _extract_script_links("action")

    assert result == [
        ("Movie 1", "2020", "https://some-website.com/live/pdf/scripts/m1.pdf"),
        ("Movie 1", "2020", "https://some-website.com/live/pdf/scripts/m1.pdf")
    ]


def test__extract_script_links_same_page(mocker):
    # mock GraphQL response
    mock_post = mocker.patch("extract_movie_data.requests.post")
    mock_post.return_value.json.return_value = {
        "data": {
            "scriptsEntries": [
                {"uri": "movie-1"},
                {"uri": "movie-1"}
            ]
        }
    }

    # mock script page fetch
    def fake_get(url):
        fake_resp = Mock()
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None

        fake_resp.content = b"""
            <a href="https://some-website.com/live/pdf/scripts/m1.pdf">PDF</a>
            <span class="text-3xl leading-normal md:text-4xl lg:text-5xl lg:leading-normal">Movie 1</span>
            <p class="font-semibold text-slate-500 font-slab text-lg">Film - 2020</p>
        """
        return fake_resp

    mocker.patch("extract_movie_data.requests.get", side_effect=fake_get)

    checked_script_pages.clear()

    result = _extract_script_links("action")

    assert result == [
        ("Movie 1", "2020", "https://some-website.com/live/pdf/scripts/m1.pdf")
    ]
    assert len(checked_script_pages) == 1


def test__extract_script_links_no_pdf_link(mocker):
    # mock GraphQL response
    mock_post = mocker.patch("extract_movie_data.requests.post")
    mock_post.return_value.json.return_value = {
        "data": {
            "scriptsEntries": [
                {"uri": "movie-1"}
            ]
        }
    }

    # mock script page fetch without PDF link
    def fake_get(url):
        fake_resp = Mock()
        fake_resp.__enter__ = lambda s: s
        fake_resp.__exit__ = lambda *a: None

        fake_resp.content = b"""
            <span class="text-3xl leading-normal md:text-4xl lg:text-5xl lg:leading-normal">Movie 1</span>
            <p class="font-semibold text-slate-500 font-slab text-lg">Film - 2020</p>
        """
        return fake_resp

    mocker.patch("extract_movie_data.requests.get", side_effect=fake_get)

    checked_script_pages.clear()

    result = _extract_script_links("action")

    assert result == []


def test__extract_and_store_movie_data(mocker):
    # Mock script links
    mocker.patch(
        "extract_movie_data._extract_script_links",
        return_value=[("Movie", "2020", "http://example.com/m.pdf")]
    )

    # Mock movie processing check
    mocker.patch("extract_movie_data._should_process_movie", return_value=True)

    # Mock PDF download
    mocker.patch("extract_movie_data.utils.download_pdf", return_value="/tmp/m.pdf")

    # Mock script extraction
    mocker.patch("extract_movie_data._extract_script_from_pdf", return_value=[{"script": True}])

    # Mock function that adds TMDB data
    mocker.patch("extract_movie_data._add_movie_data", return_value={"id": 1})

    # Mock Databricks workspace client
    mock_ws = Mock()
    mock_ws.files.upload = Mock()

    _extract_and_store_movie_data("action", mock_ws, set())

    # Validate uploaded JSON content
    args, kwargs = mock_ws.files.upload.call_args
    uploaded_path = args[0]
    uploaded_stream = args[1]

    assert uploaded_path.endswith("action_movies.json")

    json_loaded = json.loads(uploaded_stream.getvalue().decode())
    assert json_loaded == [{"id": 1}]


def test__extract_and_store_movie_data_should_not_process(mocker):
    # Mock script links
    mocker.patch(
        "extract_movie_data._extract_script_links",
        return_value=[("Movie", "2020", "http://example.com/m.pdf")]
    )

    # Mock movie processing check to return False
    mocker.patch("extract_movie_data._should_process_movie", return_value=False)

    # Mock PDF download
    mocker.patch("extract_movie_data.utils.download_pdf", return_value="/tmp/m.pdf")

    # Mock script extraction
    mocker.patch("extract_movie_data._extract_script_from_pdf", return_value=[{"script": True}])

    # Mock function that adds TMDB data
    mock_add_movie_data = mocker.patch("extract_movie_data._add_movie_data")

    # Mock Databricks workspace client
    mock_ws = Mock()
    mock_ws.files.upload = Mock()

    _extract_and_store_movie_data("action", mock_ws, set())

    # Validate that no upload occurred
    assert not mock_ws.files.upload.called

    # Validate that _add_movie_data was never called
    assert not mock_add_movie_data.called
