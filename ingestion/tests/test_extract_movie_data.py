import json
from unittest.mock import Mock, MagicMock

from extract_movie_data import (
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
    assert result is None


def test__should_process_movie_multiple_results(mocker):
    mocker.patch.object(
        tmdb_search,
        "movie",
        return_value={"results": [{"title": "Movie"}, {"title": "Movie"}]}
    )

    result = _should_process_movie("Movie", "2020", set())
    assert result is None


def test__should_process_movie_movie_already_stored(mocker):
    mocker.patch.object(
        tmdb_search,
        "movie",
        return_value={"results": [{"title": "Movie", "id": 123}]}
    )

    result = _should_process_movie("Movie", "2020", {123})
    assert result is None


def test__should_process_movie_success(mocker):
    mocker.patch.object(
        tmdb_search,
        "movie",
        return_value={"results": [{"title": "Movie", "id": 123}]}
    )

    result = _should_process_movie("Movie", "2020", set())
    assert result == 123


def test__extract_script_links(mocker):
    mock_session = Mock()
    mocker.patch.object(extract_movie_data, "session", mock_session)

    mock_post_response = Mock()
    mock_post_response.json.return_value = {
        "data": {
            "scriptsEntries": [
                {
                    "scriptTitle": "Movie 1",
                    "year": "2020",
                    "uri": "movie-1"
                }
            ]
        }
    }
    mock_post_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_post_response

    # Mock _should_process_movie
    mocker.patch(
        "extract_movie_data._should_process_movie",
        return_value=123
    )

    # Mock GET (HTML page with PDF link)
    mock_get_response = Mock()
    mock_get_response.content = b"""
        <a href="https://some-website.com/live/pdf/scripts/m1.pdf">PDF</a>
    """
    mock_get_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_get_response

    checked_script_pages.clear()

    result = _extract_script_links(("action", 1), set())

    assert result == [
        (123, "Movie 1", "2020", "https://some-website.com/live/pdf/scripts/m1.pdf")
    ]


def test__extract_script_links_not_a_movie(mocker):
    mock_session = Mock()
    mocker.patch.object(extract_movie_data, "session", mock_session)

    mock_post_response = Mock()
    mock_post_response.json.return_value = {
        "data": {
            "scriptsEntries": [
                {
                    "title": "Movie 1",  # not "scriptTitle"
                    "year": "2020",
                    "uri": "movie-1"
                }
            ]
        }
    }
    mock_post_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_post_response

    mocker.patch("extract_movie_data._should_process_movie", return_value=123)

    mock_get_response = Mock()
    mock_get_response.content = b"""
        <a href="https://some-website.com/live/pdf/scripts/m1.pdf">PDF</a>
    """
    mock_get_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_get_response

    checked_script_pages.clear()

    result = _extract_script_links(("action", 1), set())

    assert result == []


def test__extract_script_links_same_page(mocker):
    mock_session = Mock()
    mocker.patch.object(extract_movie_data, "session", mock_session)

    mock_post_response = Mock()
    mock_post_response.json.return_value = {
        "data": {
            "scriptsEntries": [
                {
                    "scriptTitle": "Movie 1",
                    "year": "2020",
                    "uri": "movie-1"
                },
                {
                    "scriptTitle": "Movie 1",
                    "year": "2020",
                    "uri": "movie-1"
                }
            ]
        }
    }
    mock_post_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_post_response

    mocker.patch("extract_movie_data._should_process_movie", return_value=123)

    mock_get_response = Mock()
    mock_get_response.content = b"""
        <a href="https://some-website.com/live/pdf/scripts/m1.pdf">PDF</a>
    """
    mock_get_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_get_response

    checked_script_pages.clear()

    result = _extract_script_links(("action", 1), set())

    assert len(result) == 1
    assert len(checked_script_pages) == 1


def test__extract_script_links_should_not_process_movie(mocker):
    mock_session = Mock()
    mocker.patch.object(extract_movie_data, "session", mock_session)

    mock_post_response = Mock()
    mock_post_response.json.return_value = {
        "data": {
            "scriptsEntries": [
                {
                    "scriptTitle": "Movie 1",
                    "year": "2020",
                    "uri": "movie-1"
                }
            ]
        }
    }
    mock_post_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_post_response

    mocker.patch("extract_movie_data._should_process_movie", return_value=None)

    mock_get_response = Mock()
    mock_get_response.content = b"""
        <a href="https://some-website.com/live/pdf/scripts/m1.pdf">PDF</a>
    """
    mock_get_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_get_response

    checked_script_pages.clear()

    result = _extract_script_links(("action", 1), set())

    assert result == []


def test__extract_script_links_no_pdf_link(mocker):
    mock_session = Mock()
    mocker.patch.object(extract_movie_data, "session", mock_session)

    mock_session = Mock()
    mocker.patch.object(extract_movie_data, "session", mock_session)

    mock_post_response = Mock()
    mock_post_response.json.return_value = {
        "data": {
            "scriptsEntries": [
                {
                    "scriptTitle": "Movie 1",
                    "year": "2020",
                    "uri": "movie-1"
                }
            ]
        }
    }
    mock_post_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_post_response

    mocker.patch("extract_movie_data._should_process_movie", return_value=123)

    mock_get_response = Mock()
    mock_get_response.content = b"<html>No PDF</html>"
    mock_get_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_get_response

    checked_script_pages.clear()

    result = _extract_script_links(("action", 1), set())

    assert result == []


def test__extract_and_store_movie_data(mocker):
    mocker.patch(
        "extract_movie_data._extract_script_links",
        return_value=[(123, "Movie", "2020", "http://example.com/m.pdf")]
    )

    mocker.patch("extract_movie_data.utils.download_pdf", return_value="/tmp/m.pdf")

    mocker.patch(
        "extract_movie_data._extract_script_from_pdf",
        return_value=[{"script": True}]
    )

    mock_tmdb_movie = Mock()
    mock_tmdb_movie.credits.return_value = {"cast": [{"name": "Actor"}]}

    mocker.patch("extract_movie_data.tmdb.Movies", return_value=mock_tmdb_movie)

    mocker.patch(
        "extract_movie_data.utils.create_character_actor_map",
        return_value={"Character": "Actor"}
    )

    mocker.patch(
        "extract_movie_data.utils.remove_null_bytes",
        side_effect=lambda x: x
    )

    mock_ws = Mock()
    mock_ws.files.upload = Mock()

    already_ids = set()

    _extract_and_store_movie_data((("action", 1), 1), mock_ws, already_ids)

    assert 123 in already_ids
    assert mock_ws.files.upload.called

    args = mock_ws.files.upload.call_args[0]
    uploaded_json = json.loads(args[1].getvalue().decode())

    assert uploaded_json == [{
        "tmdb_id": 123,
        "title": "Movie",
        "year": "2020",
        "script": [{"script": True}],
        "character_to_actor": {"Character": "Actor"}
    }]


def test__extract_and_store_movie_data_no_movies(mocker):
    mocker.patch(
        "extract_movie_data._extract_script_links",
        return_value=[]
    )

    mock_ws = Mock()
    mock_ws.files.upload = Mock()

    _extract_and_store_movie_data(("action", 1), mock_ws, set())

    assert not mock_ws.files.upload.called
