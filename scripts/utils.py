"""Small helpers used by the collection scripts."""
import logging
import time
from pathlib import Path

import requests

log = logging.getLogger("collection")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )


def get_with_retry(url, params=None, retries=5, timeout=120, stream=False):
    """GET a URL, retrying on network errors and 429/5xx responses.

    A 429 means the API rate limit was hit, so we wait a full minute before
    trying again. Other errors are retried after a short pause.
    """
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout, stream=stream)
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as err:
            status = getattr(err.response, "status_code", None)
            if attempt == retries or (status is not None and status < 500 and status != 429):
                raise
            wait = 65 if status == 429 else 5 * attempt
            log.warning("Request failed (%s), retrying in %ss", err, wait)
            time.sleep(wait)


def download_file(url, dest: Path, force=False):
    """Download url to dest. Skips the download if the file is already there."""
    dest = Path(dest)
    if dest.exists() and not force:
        log.info("Already downloaded: %s", dest.name)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log.info("Downloading %s", url)
    with get_with_retry(url, stream=True, timeout=300) as response:
        with open(tmp, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.replace(dest)
    log.info("Saved %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
    return dest
