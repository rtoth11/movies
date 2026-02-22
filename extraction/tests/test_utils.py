from unittest.mock import Mock

import pytest

import extract_movie_data
from utils import (
    download_pdf,
    _strip_trailing_asterisks,
    clean_lines,
    remove_useless_lines,
    create_character_actor_map,
)


def test_download_pdf_success(tmp_path, mocker):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"PDF-DATA"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = lambda *args: None

    mock_session = Mock()
    mock_session.get.return_value = mock_response

    output_path = tmp_path / "file.pdf"
    result = download_pdf(
        "http://example.com/file.pdf",
        str(output_path),
        session=mock_session
    )

    assert output_path.read_bytes() == b"PDF-DATA"
    assert result == str(output_path)


def test_download_pdf_fail(mocker):
    mock_response = Mock()
    mock_response.status_code = 404

    mock_session = Mock()
    mock_session.get.return_value = mock_response

    result = download_pdf(
        "http://example.com/file.pdf",
        "dummy_path.pdf",
        session=mock_session
    )

    assert result is None


@pytest.mark.parametrize(
    "input_str, expected_output, expected_flag",
    [
        ("hello*", "hello", True),
        ("hello***   ", "hello", True),
        ("hello", "hello", False),
        ("test *", "test", True)
    ]
)
def test_strip_trailing_asterisks(input_str, expected_output, expected_flag):
    cleaned, flag = _strip_trailing_asterisks(input_str)
    assert cleaned == expected_output
    assert flag is expected_flag


def test_clean_lines():
    lines = [
        "hello*",
        "world  **  ",
        "*",
        "clean line",
    ]

    cleaned, revised = clean_lines(lines)

    assert cleaned == ["hello", "world", "", "clean line"]
    assert revised is True


@pytest.mark.parametrize(
    "line, should_remove",
    [
        ("(CONTINUED)", True),
        ("(More)", True),
        ("continued: (12)", True),
        ("1", True),
        ("1.", True),
        ("30a", True),
        ("THIS IS REV.", True),
        ("SOMETHING REVISED", True),
        ("Valid line here", False),
        ("Scene 12A description", False),
    ],
)
def test_remove_useless_lines(line, should_remove):
    original = [line]
    result = remove_useless_lines(original)

    if should_remove:
        assert result == []
    else:
        assert result == [line]


def test_create_character_actor_map_exact_match():
    script = [
        {"character": "John", "type": "dialogue"},
        {"character": "MARY", "type": "empty_dialogue"},
    ]
    cast = [
        {"character": "john", "id": 10, "name": "Actor John"},
        {"character": "Mary", "id": 11, "name": "Actor Mary"},
    ]

    result = create_character_actor_map(script, cast)

    assert {"character": "John", "actor_tmdb_id": 10, "actor_name": "Actor John"} in result
    assert {"character": "MARY", "actor_tmdb_id": 11, "actor_name": "Actor Mary"} in result


def test_create_character_actor_map_substring_match():
    script = [{"character": "Dr. Smith", "type": "dialogue"}]
    cast = [
        {"character": "Prof. Dr. Smith", "id": 20, "name": "Actor A"},
        {"character": "Professor Dr. Smith", "id": 21, "name": "Actor B"},
    ]

    result = create_character_actor_map(script, cast)

    assert result == [
        {"character": "Dr. Smith", "actor_tmdb_id": 20, "actor_name": "Actor A"}
    ]


def test_create_character_actor_map_no_match():
    script = [{"character": "Alien", "type": "dialogue"}]
    cast = [{"character": "Human", "id": 50, "name": "Actor Z"}]

    result = create_character_actor_map(script, cast)

    assert result == [
        {"character": "Alien", "actor_tmdb_id": None, "actor_name": None}
    ]
