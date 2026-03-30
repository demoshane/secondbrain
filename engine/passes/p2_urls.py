"""Pass 2: extract URLs from content, stripping them to produce LinkNotes."""
import re
from urllib.parse import urlparse

from engine.passes import LinkNote

_URL_PAT = re.compile(r'https?://\S+')


def extract_urls(content: str) -> tuple[str, list[LinkNote]]:
    """Find and strip all URLs from content.

    For each unique URL, a LinkNote is produced:
      - url:   the full URL
      - title: the netloc (domain) extracted via urlparse
      - body:  the source line that contained the URL (context)

    Returns (stripped_content, list[LinkNote]) where stripped_content has
    all URLs removed and is whitespace-stripped.
    """
    link_notes: list[LinkNote] = []
    seen: set[str] = set()

    for line in content.split('\n'):
        for match in _URL_PAT.finditer(line):
            url = match.group()
            if url in seen:
                continue
            seen.add(url)
            parsed = urlparse(url)
            title = parsed.netloc or url
            link_notes.append(LinkNote(url=url, title=title, body=line.strip()))

    stripped = _URL_PAT.sub('', content).strip()
    return stripped, link_notes
