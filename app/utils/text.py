import re
import html

def format_text_html(text: str) -> str:
    """
    Format text for Telegram HTML parse mode.
    1. Escapes generic < > symbols (not valid tags).
    2. Converts **text** to <b>text</b>.
    3. Converts *text* to <i>text</i> (unless it looks like a list item).
    4. Removes Markdown headers (###).
    """
    if not text:
        return ""
        
    # 0. Basic cleaning of headers
    # Remove "### Header" -> "Header" (bold maybe?)
    # Let's just make headers bold.
    text = re.sub(r'^#{1,6}\s+(.*)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    
    # 1. Escape HTML special chars to avoid conflict
    # We escape EVERYTHING first, then un-escape our specific tags later? 
    # Or strict replacement. 
    # Safer strategy: Escape & < > first.
    text = html.escape(text, quote=False)
    
    # 2. Bold: **text** -> <b>text</b>
    # Since we escaped < and >, we can safely introduce new tags.
    # Regex for **...**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Also __...__ sometimes used for bold
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # 3. Italic: *text* -> <i>text</i>
    # Avoid matching bullet points like "* item" at start of line
    # Match *text* where * is not followed by space, or preceeded by space/start
    text = re.sub(r'(?<!\w)\*([^\s][^*]*[^\s])\*(?!\w)', r'<i>\1</i>', text)
    # Also _..._
    text = re.sub(r'(?<!\w)_([^\s][^_]*[^\s])_(?!\w)', r'<i>\1</i>', text)
    
    # 4. Monospace: `text` -> <code>text</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    # 5. Preformatted: ```code``` -> <pre>code</pre>
    # Note: re.DOTALL for multiline
    text = re.sub(r'```(.+?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)
    
    return text
