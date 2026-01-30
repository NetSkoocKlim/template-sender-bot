from collections import defaultdict

from aiogram.types import MessageEntity


def copy_text_message(message_text: str, message_entities: list[MessageEntity]):
    if not message_entities:
        copied_message: str = ""
        for char in message_text:
            if char == '>':
                copied_message += '&gt;'
            elif char == '<':
                copied_message += '&lt;'
            elif char == '&':
                copied_message += '&amp;'
            else:
                copied_message += char
        return copied_message

    format_start: defaultdict[int, list[str]] = defaultdict(list)
    format_end: defaultdict[int, list[str]] = defaultdict(list)

    entity_type_to_html_tag = {
        "bold": "b",
        "italic": "i",
        "underline": "u",
        "strikethrough": "s",
        "pre": "pre",
        "code": "code",
        "blockquote": "blockquote",
        "expandable_blockquote": "blockquote expandable",
        "spoiler": "tg-spoiler",
    }

    for entity in message_entities:
        tag = entity_type_to_html_tag.get(entity.type)
        start = entity.offset
        end = start + entity.length
        if tag:
            if entity.language:
                format_start[start].append(f"<{tag}><code class='language-{entity.language}'>")
                format_end[end].append(f"</code></{tag}>")
            else:
                if tag == "blockquote expandable":
                    format_start[start].append(f"<{tag}>")
                    format_end[end].append(f"</blockquote>")
                else:
                    format_start[start].append(f"<{tag}>")
                    format_end[end].append(f"</{tag}>")
        elif entity.url:
            format_start[start].append(f"<a href='{entity.url}'>")
            format_end[end].append(f"</a>")

    copied_message: str = ""
    for index, char in enumerate(message_text):
        if format_end[index]:
            copied_message += ''.join(format_end[index][::-1])
        if format_start[index]:
            copied_message += ''.join(format_start[index])

        if char == '>':
            copied_message += '&gt;'
        elif char == '<':
            copied_message += '&lt;'
        elif char == '&':
            copied_message += '&amp;'
        else:
            copied_message += char

    if format_end.get(len(message_text)):
        copied_message += ''.join(format_end[len(message_text)][::-1])

    return copied_message
