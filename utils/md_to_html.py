import re
import html

def md_to_html(text: str) -> str:
    segments = []
    last = 0

    fence_pattern = re.compile(r"```(\w*)\n?(.*?)```", re.DOTALL)
    for m in fence_pattern.finditer(text):
        if m.start() > last:
            segments.append((False, text[last:m.start()]))
        lang = m.group(1).strip()
        code = html.escape(m.group(2))
        tag = f'<pre><code class="language-{lang}">{code}</code></pre>' if lang else f"<pre>{code}</pre>"
        segments.append((True, tag))
        last = m.end()
    if last < len(text):
        segments.append((False, text[last:]))

    result = []
    for is_code, chunk in segments:
        if is_code:
            result.append(chunk)
            continue

        chunk = html.escape(chunk)

        # Protect inline code
        inline_codes = {}
        def save_inline(m):
            key = f"\x00INLINE{len(inline_codes)}\x00"
            inline_codes[key] = f"<code>{html.escape(m.group(1))}</code>"
            return key
        chunk = re.sub(r"`([^`\n]+)`", save_inline, chunk)

        # Bold
        chunk = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", chunk)
        chunk = re.sub(r"__(.+?)__", r"<b>\1</b>", chunk)

        # Italic (single * or _, but not bullet points at line start)
        chunk = re.sub(r"(?<!\n)\*(?!\*)(.+?)(?<!\*)\*", r"<i>\1</i>", chunk)
        chunk = re.sub(r"_(?!_)(.+?)(?<!_)_", r"<i>\1</i>", chunk)

        # Strikethrough
        chunk = re.sub(r"~~(.+?)~~", r"<s>\1</s>", chunk)

        # Links
        chunk = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r'<a href="\2">\1</a>', chunk)

        # Headers → bold
        chunk = re.sub(r"^#{1,3}\s+(.+)$", r"<b>\1</b>", chunk, flags=re.MULTILINE)

        # Bullet points: * item or - item → • item
        chunk = re.sub(r"^\*\s+(.+)$", r"• \1", chunk, flags=re.MULTILINE)
        chunk = re.sub(r"^-\s+(.+)$", r"• \1", chunk, flags=re.MULTILINE)

        # Numbered lists: 1. item → keep as-is but strip extra indent
        chunk = re.sub(r"^\d+\.\s+(.+)$", lambda m: m.group(0).strip(), chunk, flags=re.MULTILINE)

        # Horizontal rule
        chunk = re.sub(r"^[-*]{3,}$", "─────────────", chunk, flags=re.MULTILINE)

        # Restore inline codes
        for key, val in inline_codes.items():
            chunk = chunk.replace(key, val)

        result.append(chunk)

    return "".join(result)
