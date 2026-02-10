import textwrap

_INDENT_SCENE = " " * 8
_INDENT_DESCRIPTION = " " * 8
_INDENT_CHARACTER = " " * 24
_INDENT_DIALOGUE = " " * 18
_INDENT_PAREN = " " * 24


def format_scene(text):
    scene = textwrap.indent(text, _INDENT_SCENE)
    return f"\n{scene}\n\n"


def format_dialogue(character, dialogue, suffix, parenthetical):
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


def format_description(text):
    return textwrap.indent(text, _INDENT_DESCRIPTION) + "\n"


def generate_script(blocks):
    script = ""

    for block in sorted(blocks, key=lambda b: b["index_in_script"]):
        if block["type"] == "scene":
            line = format_scene(block["content"])

        elif block["type"] == "dialogue":
            line = format_dialogue(block["character"],
                                   block["content"],
                                   block["suffix"],
                                   block["parentheticals"])

        elif block["type"] == "empty_dialogue":
            line = format_dialogue(block["character"],
                                    "<DIALOGUE MISSING>",
                                    "",
                                    "")

        elif block["type"] == "description":
            line = format_description(block["content"])

        else:
            line = block["content"] + "\n"

        script += line

    return script
