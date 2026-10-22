"""Unit tests for video frame extraction (src/eelgrass_intelligence/video_frames.py).

Every test video used here is generated on the fly with OpenCV's own
VideoWriter — no real survey footage, no copyrighted video, and no
internet access is involved anywhere in this file.
"""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from eelgrass_intelligence.video_frames import (
    MANIFEST_FILENAME,
    FrameExtractionError,
    extract_frames,
)

# How far a reported frame timestamp is allowed to drift from the exact
# mathematical expectation (frame_index / fps seconds) before a test
# considers it wrong. OpenCV's reported timestamps are not bit-exact (see
# video_frames.py's module docstring on timestamp accuracy); this generous
# tolerance accounts for floating point and container-level rounding while
# still catching a genuinely broken timestamp.
TIMESTAMP_TOLERANCE_SECONDS = 0.05


def _make_synthetic_video(
    path: Path,
    *,
    fps: float = 10.0,
    num_frames: int = 50,
    width: int = 64,
    height: int = 48,
) -> None:
    """Write a tiny, deterministic synthetic video to `path`.

    Each frame is a single solid colour that changes slightly from the
    last, so frames are distinguishable from one another if ever
    inspected, without this test depending on any real imagery.
    """
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    try:
        for frame_number in range(num_frames):
            colour_value = frame_number % 256
            frame = np.full((height, width, 3), colour_value, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


@pytest.fixture
def synthetic_video(tmp_path: Path) -> Path:
    """A 5-second, 10 fps synthetic video (50 frames total)."""
    video_path = tmp_path / "synthetic.mp4"
    _make_synthetic_video(video_path, fps=10.0, num_frames=50)
    return video_path


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- Successful extraction ---


def test_extraction_at_default_interval(synthetic_video: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "frames_default"

    manifest = extract_frames(synthetic_video, output_dir)

    # 5 seconds of video at the default 1-frame-per-second interval should
    # yield 5 frames (timestamps 0.0, 1.0, 2.0, 3.0, 4.0 seconds).
    assert len(manifest.frames) == 5
    assert manifest.extraction_interval_seconds == 1.0

    for frame in manifest.frames:
        frame_path = output_dir / frame.filename
        assert frame_path.exists()


def test_extraction_with_custom_interval(synthetic_video: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "frames_custom"

    # Every 2 seconds across a 5-second video: timestamps 0.0, 2.0, 4.0.
    manifest = extract_frames(synthetic_video, output_dir, interval_seconds=2.0)

    assert len(manifest.frames) == 3
    assert manifest.extraction_interval_seconds == 2.0


def test_frame_count_and_ordering(synthetic_video: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "frames_ordering"

    manifest = extract_frames(synthetic_video, output_dir, interval_seconds=1.0)

    indices = [frame.frame_index for frame in manifest.frames]
    assert indices == sorted(indices)
    assert indices == list(range(len(manifest.frames)))

    timestamps = [frame.timestamp_seconds for frame in manifest.frames]
    assert timestamps == sorted(timestamps)

    filenames = [frame.filename for frame in manifest.frames]
    assert filenames == [f"frame_{i:06d}.png" for i in range(len(manifest.frames))]


def test_timestamps_within_documented_tolerance(synthetic_video: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "frames_timestamps"

    manifest = extract_frames(synthetic_video, output_dir, interval_seconds=1.0)

    for frame in manifest.frames:
        expected_seconds = frame.frame_index * 1.0
        assert abs(frame.timestamp_seconds - expected_seconds) <= TIMESTAMP_TOLERANCE_SECONDS

        expected_milliseconds = expected_seconds * 1000.0
        assert (
            abs(frame.timestamp_milliseconds - expected_milliseconds)
            <= TIMESTAMP_TOLERANCE_SECONDS * 1000.0
        )
        # Milliseconds and seconds must always agree with each other.
        assert frame.timestamp_milliseconds == pytest.approx(
            frame.timestamp_seconds * 1000.0
        )


# --- Manifest content ---


def test_manifest_schema_and_required_metadata(synthetic_video: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "frames_manifest"

    manifest = extract_frames(synthetic_video, output_dir, interval_seconds=1.0)

    manifest_path = output_dir / MANIFEST_FILENAME
    assert manifest_path.exists()

    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert on_disk["schema_version"] == 1
    assert on_disk["source_video_filename"] == synthetic_video.name
    assert on_disk["source_video_size_bytes"] == synthetic_video.stat().st_size
    assert on_disk["source_video_sha256"] == _sha256_of(synthetic_video)
    assert on_disk["extraction_interval_seconds"] == 1.0
    assert "opencv-python-headless" in on_disk["extraction_library"]

    # These are "best effort" fields: present as keys, but may legally be
    # null if the video's container didn't report them. For our synthetic
    # 10fps/50-frame video OpenCV does report them, so we check real
    # values here, not just key presence.
    assert on_disk["source_video_reported_fps"] == pytest.approx(10.0)
    assert on_disk["source_video_reported_frame_count"] == 50
    assert on_disk["source_video_duration_seconds"] == pytest.approx(5.0)

    assert isinstance(on_disk["frames"], list)
    assert len(on_disk["frames"]) == len(manifest.frames)
    first_frame = on_disk["frames"][0]
    assert set(first_frame) == {
        "frame_index",
        "filename",
        "timestamp_seconds",
        "timestamp_milliseconds",
    }

    # No survey/location/label metadata must ever appear in the manifest,
    # even as a null placeholder — this ingestion step must not invent
    # fields it has no validated source for.
    forbidden_keys = {
        "survey_id",
        "location",
        "coordinates",
        "latitude",
        "longitude",
        "date",
        "label",
        "cover_type",
        "eelgrass_present",
    }
    assert forbidden_keys.isdisjoint(on_disk.keys())


def test_manifest_frame_paths_are_relative(synthetic_video: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "frames_relative"

    manifest = extract_frames(synthetic_video, output_dir, interval_seconds=1.0)

    for frame in manifest.frames:
        assert not Path(frame.filename).is_absolute()
        assert ".." not in Path(frame.filename).parts


# --- Source checksum correctness ---


def test_source_checksum_matches_independently_computed_hash(
    synthetic_video: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "frames_checksum"

    manifest = extract_frames(synthetic_video, output_dir)

    assert manifest.source_video_sha256 == _sha256_of(synthetic_video)


# --- Input validation and error handling ---


def test_nonexistent_video_raises_clear_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "does_not_exist.mp4"

    with pytest.raises(FrameExtractionError, match="not found"):
        extract_frames(missing_path, tmp_path / "out")


def test_directory_as_video_path_raises_clear_error(tmp_path: Path) -> None:
    directory_path = tmp_path / "a_directory"
    directory_path.mkdir()

    with pytest.raises(FrameExtractionError, match="directory"):
        extract_frames(directory_path, tmp_path / "out")


@pytest.mark.parametrize("bad_interval", [0, -1, -0.5, 0.0])
def test_invalid_interval_raises_clear_error(
    synthetic_video: Path, tmp_path: Path, bad_interval: float
) -> None:
    with pytest.raises(FrameExtractionError, match="positive"):
        extract_frames(synthetic_video, tmp_path / "out", interval_seconds=bad_interval)


def test_unreadable_corrupt_video_raises_clear_error(tmp_path: Path) -> None:
    corrupt_path = tmp_path / "corrupt.mp4"
    # Plain garbage bytes, not a real video container.
    corrupt_path.write_bytes(b"this is not a real video file" * 1000)

    with pytest.raises(FrameExtractionError, match="Could not open video"):
        extract_frames(corrupt_path, tmp_path / "out")


def test_empty_video_file_raises_clear_error(tmp_path: Path) -> None:
    empty_path = tmp_path / "empty.mp4"
    empty_path.write_bytes(b"")

    with pytest.raises(FrameExtractionError, match="Could not open video"):
        extract_frames(empty_path, tmp_path / "out")


def test_zero_frame_video_raises_clear_error(tmp_path: Path) -> None:
    # A "video" container with a valid header but no frames ever written
    # to it. OpenCV can sometimes still "open" such a file; this test
    # ensures that case is still treated as a failure, not a silently
    # successful empty extraction.
    zero_frame_path = tmp_path / "zero_frames.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(zero_frame_path), fourcc, 10.0, (64, 48))
    writer.release()

    with pytest.raises(FrameExtractionError):
        extract_frames(zero_frame_path, tmp_path / "out")


def test_existing_output_destination_rejected_without_overwrite(
    synthetic_video: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "frames_existing"

    extract_frames(synthetic_video, output_dir)

    with pytest.raises(FrameExtractionError, match="already contains a previous extraction"):
        extract_frames(synthetic_video, output_dir)


def test_existing_output_destination_allowed_with_overwrite(
    synthetic_video: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "frames_overwrite"

    first = extract_frames(synthetic_video, output_dir, interval_seconds=1.0)
    second = extract_frames(synthetic_video, output_dir, interval_seconds=2.0, overwrite=True)

    assert first.extraction_interval_seconds == 1.0
    assert second.extraction_interval_seconds == 2.0
    # The manifest on disk must reflect the second (overwriting) run.
    on_disk = json.loads((output_dir / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert on_disk["extraction_interval_seconds"] == 2.0


# --- Source video left unchanged ---


def test_source_video_is_not_modified(synthetic_video: Path, tmp_path: Path) -> None:
    checksum_before = _sha256_of(synthetic_video)
    size_before = synthetic_video.stat().st_size

    extract_frames(synthetic_video, tmp_path / "frames_unchanged")

    assert synthetic_video.exists()
    assert synthetic_video.stat().st_size == size_before
    assert _sha256_of(synthetic_video) == checksum_before
