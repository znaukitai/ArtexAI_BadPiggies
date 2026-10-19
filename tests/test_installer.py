"""Release integrity checks before installing a downloaded archive."""

import hashlib

import pytest

from installer.install_from_release import verify_archive


def test_release_checksum_accepts_exact_archive(tmp_path):
    archive = tmp_path / "download.zip"
    archive.write_bytes(b"release payload")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    verify_archive(archive, f"{digest}  ArtexAI-win64.zip\n")


@pytest.mark.parametrize("checksums", ["", "0" * 64 + "  ArtexAI-win64.zip", "0" * 64 + "  other.zip"])
def test_release_checksum_rejects_missing_or_modified_download(tmp_path, checksums):
    archive = tmp_path / "download.zip"
    archive.write_bytes(b"modified payload")
    with pytest.raises(RuntimeError, match="Контрольная сумма"):
        verify_archive(archive, checksums)
