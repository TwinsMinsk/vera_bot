import re
import html

def format_text_html(text: str) -> str:
    """
    Format text for Telegram HTML parse mode.
    Correct Logic:
    1. Escape ENTIRE text first (so User's <script> becomes &lt;script&gt;).
    2. THEN restore/convert Markdown patterns to validated HTML tags.
    """
    if not text:
        return ""
        
    # 1. Escape everything first
    text = html.escape(text, quote=False)
    
    # 2. Bold: **text** or __text__ -> <b>text</b>
    # Note: re.sub will operate on the escaped string.
    # Markdown usually doesn't care about &lt; inside logic unless strictly defined.
    # We match **...**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # 3. Italic: *text* or _text_ -> <i>text</i>
    # Avoid matching inside words if possible, but basic * logic:
    text = re.sub(r'(?<!\w)\*([^\s][^*]*[^\s])\*(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_([^\s][^_]*[^\s])_(?!\w)', r'<i>\1</i>', text)
    
    # 4. Monospace: `text` -> <code>text</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    # 5. Preformatted: ```code``` -> <pre>code</pre>
    text = re.sub(r'```(.+?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)
    
    # 6. Links: [text](url) -> <a href="url">text</a>
    # Note: URL might be escaped! e.g. foo&amp;bar
    # We should match parentheses carefully.
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    
    # 7. Headers: ### Header -> <b>Header</b>
    # Header usually implies new line.
    text = re.sub(r'^#{1,6}\s+(.*)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    
    return text
