"""Maps original VK media URLs to the locally downloaded files produced by the
two HTTrack mirrors inside vk_chat (projects "41" and "VkOpt/45").

The HTTrack cache file `hts-cache/new.txt` is a TSV whose 8th column is the
original URL and 9th column is the absolute local path on the machine that did
the download. We resolve those to the files actually present under each web dir.
"""
import os

import config

_MIRRORS: list[tuple[str, str]] | None = None
_MAP: dict[str, str] | None = None


def _mirror_list() -> list[tuple[str, str]]:
    """Execute the mirror list operation."""
    mirrors = getattr(config, "VK_MEDIA_MIRRORS", None) or []
    if mirrors:
        return list(mirrors)
    # Legacy fallback relative to project root
    root = config.BASE_DIR
    return [
        (os.path.join(root, "vk_chat", "41", "hts-cache", "new.txt"),
         os.path.join(root, "vk_chat", "41", "web")),
        (os.path.join(root, "vk_chat", "VkOpt", "45", "hts-cache", "new.txt"),
         os.path.join(root, "vk_chat", "VkOpt", "45", "web")),
    ]


def reset():
    """Execute the reset operation."""
    global _MAP, _MIRRORS
    _MAP = None
    _MIRRORS = None


def _parse(newtxt: str, webdir: str, out: dict):
    """Execute the parse operation."""
    if not os.path.exists(newtxt):
        return
    with open(newtxt, encoding="utf-8", errors="replace") as f:
        next(f, None)  # header
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9:
                continue
            url, local = parts[7], parts[8]
            if not url.startswith("http"):
                continue
            name = local.replace("\\", "/").split("/")[-1]
            path = os.path.join(webdir, name)
            if os.path.exists(path):
                out.setdefault(url, path)


def _build() -> dict:
    """Execute the build operation."""
    out: dict[str, str] = {}
    mirrors = _mirror_list()
    for newtxt, webdir in reversed(mirrors):
        _parse(newtxt, webdir, out)
    return out


def lookup(url: str | None) -> str | None:
    """Execute the lookup operation."""
    global _MAP
    if _MAP is None:
        _MAP = _build()
    if not url:
        return None
    return _MAP.get(url)


def size() -> int:
    """Execute the size operation."""
    global _MAP
    if _MAP is None:
        _MAP = _build()
    return len(_MAP)
