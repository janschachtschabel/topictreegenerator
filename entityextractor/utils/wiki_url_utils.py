import urllib.parse

def sanitize_wikipedia_url(url):
    """
    Ensure the Wikipedia URL is correctly encoded (especially for German/Umlaut/Sonderzeichen).
    Only encodes the article title part after '/wiki/'.
    """
    if "/wiki/" in url:
        base, title = url.split("/wiki/", 1)
        # Replace spaces with underscores (Wikipedia standard)
        title = title.replace(" ", "_")
        title_encoded = urllib.parse.quote(title, safe="_()%-")
        return f"{base}/wiki/{title_encoded}"
    return url
