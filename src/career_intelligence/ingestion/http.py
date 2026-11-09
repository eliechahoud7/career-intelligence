"""Generic, dependency-light file downloader used by all bulk-download connectors.

Features: retries with exponential backoff on transient errors, streaming to a
temporary ``.part`` file, SHA-256 checksum, optional file-signature check, and an
atomic rename so a failed download never leaves a truncated file in place.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from career_intelligence.utils.logging import get_logger

logger = get_logger(__name__)

# First bytes of a ZIP container — .xlsx files are ZIP archives.
ZIP_MAGIC = b"PK\x03\x04"


class DownloadError(RuntimeError):
    """Raised when a download fails or its content is not what was expected."""


@dataclass(frozen=True)
class DownloadResult:
    url: str
    path: Path
    sha256: str
    size_bytes: int
    content_type: str | None
    downloaded_at: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["path"] = str(self.path)
        return data


def build_session(
    max_retries: int = 3, backoff_factor: float = 1.0, user_agent: str | None = None
) -> requests.Session:
    """Create a requests session that retries idempotent GETs on transient failures."""
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    if user_agent:
        session.headers["User-Agent"] = user_agent
    return session


def sha256_of(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(
    url: str,
    dest: Path,
    *,
    session: requests.Session | None = None,
    timeout: float = 30,
    expected_magic: bytes | None = None,
    min_size_bytes: int = 1,
    chunk_size: int = 1 << 16,
) -> DownloadResult:
    """Download ``url`` to ``dest`` atomically and return its metadata.

    Args:
        expected_magic: if given, the file must start with these bytes
            (guards against HTML error pages served with HTTP 200).
        min_size_bytes: reject suspiciously small files.
    """
    session = session or build_session()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    digest = hashlib.sha256()
    size = 0
    header = b""

    logger.info("Downloading %s", url)
    try:
        with session.get(url, stream=True, timeout=timeout) as response:
            if response.status_code != 200:
                raise DownloadError(f"HTTP {response.status_code} for {url}")
            content_type = response.headers.get("Content-Type")
            with tmp.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    if len(header) < 8:
                        header += chunk[: 8 - len(header)]
                    digest.update(chunk)
                    size += len(chunk)
                    fh.write(chunk)
    except requests.RequestException as exc:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"Request failed for {url}: {exc}") from exc
    except DownloadError:
        tmp.unlink(missing_ok=True)
        raise

    if size < min_size_bytes:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"Downloaded file too small ({size} B) from {url}")
    if expected_magic and not header.startswith(expected_magic):
        tmp.unlink(missing_ok=True)
        raise DownloadError(
            f"Unexpected file signature from {url} (content-type={content_type}); "
            "the server may have returned an error page."
        )

    os.replace(tmp, dest)
    result = DownloadResult(
        url=url,
        path=dest,
        sha256=digest.hexdigest(),
        size_bytes=size,
        content_type=content_type,
        downloaded_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    logger.info("Saved %s (%d bytes, sha256=%s…)", dest, size, result.sha256[:12])
    return result
