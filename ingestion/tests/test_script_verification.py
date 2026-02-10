from unittest.mock import mock_open, call

from script_verification import (
    _format_scene,
    _format_dialogue,
    _format_description,
    write_blocks_to_txt,
    _INDENT_SCENE,
    _INDENT_DESCRIPTION,
    _INDENT_CHARACTER,
    _INDENT_DIALOGUE,
    _INDENT_PAREN,
)


def test_format_scene():
    input_text = "EXT. FOREST - DAY"
    expected = (
        "\n"
        + _INDENT_SCENE + "EXT. FOREST - DAY\n"
        "\n"
    )

    output = _format_scene(input_text)
    assert output == expected


def test_format_dialogue_with_suffix_and_parenthetical():
    character = "JOHN"
    dialogue = "Hello there."
    suffix = "O.S."
    parenthetical = "whispering, softly"

    expected = (
        f"{_INDENT_CHARACTER}JOHN (O.S.)\n"
        f"{_INDENT_PAREN}(softly)\n"
        f"{_INDENT_DIALOGUE}Hello there.\n"
    )

    output = _format_dialogue(character, dialogue, suffix, parenthetical)
    assert output == expected


def test_format_dialogue_no_suffix_no_parenthetical():
    character = "MARY"
    dialogue = "I know."
    suffix = ""
    parenthetical = ""

    expected = (
        f"{_INDENT_CHARACTER}MARY\n"
        f"{_INDENT_DIALOGUE}I know.\n"
    )

    output = _format_dialogue(character, dialogue, suffix, parenthetical)
    assert output == expected


def test_format_description():
    text = "The room is dark."
    expected = _INDENT_DESCRIPTION + "The room is dark.\n"

    output = _format_description(text)
    assert output == expected


def test_write_blocks_to_txt(mocker):
    mock_file = mock_open()
    mocker.patch("builtins.open", mock_file)

    blocks = [
        {
            "type": "scene",
            "content": "INT. HOUSE - DAY"
        },
        {
            "type": "dialogue",
             "character": "JOHN",
             "dialogue": "Hello!",
             "suffix": "O.S.",
             "parentheticals": "angry"
        },
        {
            "type": "empty_dialogue",
            "character": "MARY"
        },
        {
            "type": "description",
            "content": "A quiet room."
        },
        {
            "type": "other",
            "content": "Raw text block"
        }
    ]

    write_blocks_to_txt(blocks, "output_file")

    # collect all writes
    handle = mock_file()

    expected_scene = _format_scene("INT. HOUSE - DAY")
    expected_dialogue = _format_dialogue("JOHN", "Hello!", "O.S.", "angry")
    expected_empty = _format_dialogue("MARY", "<DIALOGUE MISSING>", "", "")
    expected_description = _format_description("A quiet room.")
    expected_other = "Raw text block\n"

    expected_calls = [
        call.write(expected_scene),
        call.write(expected_dialogue),
        call.write(expected_empty),
        call.write(expected_description),
        call.write(expected_other),
    ]

    handle.write.assert_has_calls(expected_calls, any_order=False)
