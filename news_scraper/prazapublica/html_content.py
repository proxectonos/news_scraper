"""
Module for cleaning HTML content using the newspaper library.
"""
import re
import newspaper


def clean_chars(content):
    """
    Cleans unwanted control characters from the content.
    """
    if isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8", errors="replace")

    return re.sub(
        r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]",
        " ",
        content
    ).strip()


def clean_html_body(html_content):
    """
    Cleans the given HTML content.

    :param: html_content (str): The raw HTML content.
    :returns: str: The cleaned text extracted from the HTML.
    """
    cleaned = clean_chars(html_content)
    if not cleaned:
        raise RuntimeError("Empty content in HTML.")

    try:
        art = newspaper.article(url="https://praza.gal", input_html=cleaned)
        html_cleaned = art.to_json(as_string=False).get('text', '')
    except Exception:
        html_cleaned = ""

    if not html_cleaned:
        try:
            html_cleaned = newspaper.fulltext(cleaned).strip()
        except Exception:
            html_cleaned = ""

    if not html_cleaned:
        raise RuntimeError("newspaper failed to clean HTML content.")

    return html_cleaned
