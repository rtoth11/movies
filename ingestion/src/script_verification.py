import textwrap

_INDENT_SCENE = " " * 8
_INDENT_DESCRIPTION = " " * 8
_INDENT_CHARACTER = " " * 24
_INDENT_DIALOGUE = " " * 18
_INDENT_PAREN = " " * 24


def _format_scene(text):
    scene = textwrap.indent(text, _INDENT_SCENE)
    return f"\n{scene}\n\n"


def _format_dialogue(character, dialogue, suffix, parenthetical):
    suffix_text = f" ({suffix})" if suffix else ""
    parenthetical_text = (
        f"{_INDENT_PAREN}({parenthetical.split(', ')[-1]})\n" if parenthetical else ""
    )

    dialogue = textwrap.indent(dialogue, _INDENT_DIALOGUE)

    return (
        f"{_INDENT_CHARACTER}{character}{suffix_text}\n"
        f"{parenthetical_text}"
        f"{dialogue}\n"
    )


def _format_description(text):
    return textwrap.indent(text, _INDENT_DESCRIPTION) + "\n"


def write_blocks_to_txt(blocks, file_name):
    with open(f"{file_name}.txt", "w", encoding="utf-8") as f:
        for block in blocks:
            if block["type"] == "scene":
                line = _format_scene(block["content"])

            elif block["type"] == "dialogue":
                line = _format_dialogue(block["character"],
                                        block["dialogue"],
                                        block["suffix"],
                                        block["parentheticals"])

            elif block["type"] == "empty_dialogue":
                line = _format_dialogue(block["character"],
                                        "<DIALOGUE MISSING>",
                                        "",
                                        "")

            elif block["type"] == "description":
                line = _format_description(block["content"])

            else:
                line = block["content"] + "\n"

            f.write(line)
