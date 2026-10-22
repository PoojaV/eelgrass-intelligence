"""Extract still frames from a local survey video, at a fixed time interval.

This module is a Layer 1/2 ingestion capability (see docs/architecture.md):
it turns one video file into a set of timestamped image frames and a JSON
manifest describing exactly how they were produced. It does NOT look at
pixel content, classify anything, or compute eelgrass presence/cover — see
docs/decisions/0001-segmentation-as-provisional-working-hypothesis.md for
why those remain separate, unvalidated milestones.

Why OpenCV ("cv2")?
-------------------
Reading and decoding video frame-by-frame needs a video-decoding library.
OpenCV's Python package (installed as "opencv-python-headless") was
chosen because:

- It is installed with a normal `pip install`, with no separately
  installed system executable (e.g. no standalone ffmpeg binary) required.
- It already depends on NumPy, which this project uses elsewhere
  (see masks.py), so it does not pull in an unrelated array library.
- The "headless" variant has no GUI/display dependency, which fits a
  library meant to run in a script, a test suite, or (later) a server.

How "approximately one frame per second" actually works
---------------------------------------------------------
A video file does not necessarily have a perfectly constant frame rate.
Rather than assuming a constant frame rate and computing which frame
*index* should land every N seconds (which would be wrong for a
variable-frame-rate, "VFR", video), this module reads each decoded
frame's own reported timestamp (OpenCV's `CAP_PROP_POS_MSEC`) and keeps a
frame whenever that timestamp has reached the next multiple of the
requested interval. This matches how long the video actually says each
frame lasted, rather than how long we assume it lasted.

Known limitation: `CAP_PROP_POS_MSEC` accuracy depends on the video
container/codec and on OpenCV's underlying decoder (FFmpeg). For most
standard, constant-frame-rate (CFR) video this is accurate to within a
fraction of a frame. For unusual or heavily variable-frame-rate video,
timestamps may be less precise; this module does not attempt to detect or
correct that, it only reports what the decoder provides. See the
"timestamp accuracy" note in `ExtractionManifest` and the project's test
suite for the tolerance this module is actually tested against.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import cv2

# The version of the manifest file's structure (not the version of any
# particular video or extraction run). Bumping this would be a deliberate,
# documented change to the manifest format.
MANIFEST_SCHEMA_VERSION = 1

# The manifest file written into every extraction output directory.
MANIFEST_FILENAME = "manifest.json"

# Frame image filenames look like "frame_000000.png", "frame_000001.png",
# etc. Six digits comfortably supports a multi-hour video at one frame per
# second (well under 1,000,000 frames) while keeping filenames sortable as
# plain text, in the same order as their frame index.
FRAME_FILENAME_TEMPLATE = "frame_{index:06d}.png"

# Frames are saved as PNG: a lossless format, so extraction never
# introduces compression artifacts beyond what the source video already
# has. This matches the PNG convention already used elsewhere in this
# project (see scripts/sample_data/).
FRAME_IMAGE_SUFFIX = ".png"

# Read and hash the source video in fixed-size chunks, rather than loading
# the whole file into memory, so hashing a large video does not require
# holding it all in RAM at once.
_HASH_CHUNK_SIZE_BYTES = 1024 * 1024


class FrameExtractionError(ValueError):
    """Raised when video frame extraction cannot proceed or fails: a
    missing or unreadable video, an invalid extraction interval, an
    existing output destination (without explicit permission to
    overwrite it), or a video that could not be decoded."""


def _opencv_python_version() -> str:
    """Return the installed opencv-python-headless package version, or
    "unknown" if it cannot be determined.

    This is recorded in every manifest, so a result can always be traced
    back to exactly which version of the extraction library produced it.
    """
    for distribution_name in ("opencv-python-headless", "opencv-python"):
        try:
            return version(distribution_name)
        except PackageNotFoundError:
            continue
    return "unknown"


def _sha256_of_file(path: Path) -> str:
    """Compute the SHA-256 checksum of a file on disk, reading it in
    fixed-size chunks rather than all at once.

    Trade-off: hashing requires reading the entire source video once,
    which takes time proportional to its size (typically a second or two
    per gigabyte on ordinary hardware). This project's expected inputs are
    short individual survey videos, not large archival footage, so this
    cost is accepted in exchange for being able to prove, later, that a
    given set of extracted frames really did come from a specific,
    unmodified source file.
    """
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        while True:
            chunk = source_file.read(_HASH_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ExtractedFrame:
    """One extracted frame's position in the source video and on disk."""

    frame_index: int
    filename: str
    timestamp_seconds: float
    timestamp_milliseconds: float


@dataclass(frozen=True)
class ExtractionManifest:
    """A full, traceable record of one frame-extraction run.

    This is both returned to Python callers and written to disk as
    `manifest.json` (see `write_json`). Every field is either a fact
    measured directly from the source video and the extraction process
    itself, or explicitly `None` when that fact could not be determined —
    never a guess or an invented value. In particular, this manifest
    never includes survey identifiers, coordinates, dates, labels, or any
    other environmental metadata: those are out of scope for this
    ingestion step and must come from a separately validated interface if
    and when they exist.
    """

    schema_version: int
    source_video_filename: str
    source_video_size_bytes: int
    source_video_sha256: str
    extraction_interval_seconds: float
    extraction_library: str
    # These three are "best effort": OpenCV reports them from the video's
    # own container metadata, which is not always present or accurate.
    # `None` means "not reported by the video," not "zero."
    source_video_duration_seconds: float | None
    source_video_reported_fps: float | None
    source_video_reported_frame_count: int | None
    frames: list[ExtractedFrame]

    def to_json_dict(self) -> dict:
        """Return a plain, JSON-serializable dict of this manifest."""
        return asdict(self)

    def write_json(self, path: Path) -> None:
        """Write this manifest to `path` as formatted JSON."""
        path.write_text(json.dumps(self.to_json_dict(), indent=2), encoding="utf-8")


def _validate_inputs(
    video_path: Path, output_dir: Path, interval_seconds: float, overwrite: bool
) -> None:
    """Validate extraction arguments before opening the video at all.

    Raises
    ------
    FrameExtractionError
        If `video_path` does not exist, is a directory, is not a positive
        number of seconds for `interval_seconds`, or if `output_dir`
        already contains a previous extraction's manifest and `overwrite`
        is not explicitly set.
    """
    if not video_path.exists():
        raise FrameExtractionError(f"Video file not found: {video_path}")

    if video_path.is_dir():
        raise FrameExtractionError(
            f"Expected a video file, but got a directory: {video_path}"
        )

    if not isinstance(interval_seconds, (int, float)) or isinstance(interval_seconds, bool):
        raise FrameExtractionError(
            f"Extraction interval must be a number of seconds, got "
            f"{type(interval_seconds).__name__}."
        )

    if interval_seconds <= 0:
        raise FrameExtractionError(
            f"Extraction interval must be a positive number of seconds, "
            f"got {interval_seconds}."
        )

    existing_manifest_path = output_dir / MANIFEST_FILENAME
    if existing_manifest_path.exists() and not overwrite:
        raise FrameExtractionError(
            f"Output directory {output_dir} already contains a previous "
            f"extraction ({existing_manifest_path.name}). Pass "
            "overwrite=True (or --overwrite on the command line) to "
            "replace it, or choose a different output directory."
        )


def extract_frames(
    video_path: Path,
    output_dir: Path,
    interval_seconds: float = 1.0,
    *,
    overwrite: bool = False,
) -> ExtractionManifest:
    """Extract frames from `video_path` at `interval_seconds` intervals.

    The source video at `video_path` is only ever opened for reading — it
    is never modified or deleted. Extracted frames and a `manifest.json`
    describing them are written into `output_dir`, which is created if it
    does not already exist.

    Parameters
    ----------
    video_path:
        Path to a local video file to read frames from.
    output_dir:
        Directory to write extracted frame images and the manifest into.
        `data/interim/<something>/` is this project's documented default
        location for this kind of derived data (see docs/architecture.md,
        Layer 1), but callers may pass any destination.
    interval_seconds:
        How often to keep a frame, in seconds. Defaults to 1.0 (one frame
        per second), matching CERI's preliminary, unconfirmed description
        of their own frame-extraction interval. Must be a positive number.
    overwrite:
        If `output_dir` already contains a manifest from a previous
        extraction, this call raises `FrameExtractionError` unless
        `overwrite=True` is passed. This exists so an extraction can never
        silently replace a previous one.

    Returns
    -------
    ExtractionManifest
        A full record of the extraction: the source video's identifying
        details, the interval used, and every extracted frame's index,
        filename, and timestamp.

    Raises
    ------
    FrameExtractionError
        If `video_path` does not exist or is a directory, if
        `interval_seconds` is not a positive number, if `output_dir`
        already holds a manifest and `overwrite` was not set, if the
        video cannot be opened/decoded by OpenCV, or if zero frames could
        be read from an otherwise "opened" video file.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    _validate_inputs(video_path, output_dir, interval_seconds, overwrite)

    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            raise FrameExtractionError(
                f"Could not open video file (unreadable, unsupported, or "
                f"corrupt): {video_path}"
            )

        reported_fps = capture.get(cv2.CAP_PROP_FPS)
        reported_frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)

        # OpenCV reports 0 (or occasionally a negative value) for these
        # properties when the video's container does not provide them, or
        # when the value could not be determined. We treat those as "not
        # reported" (None) rather than passing through a misleading 0.
        source_video_reported_fps = reported_fps if reported_fps > 0 else None
        source_video_reported_frame_count = (
            int(reported_frame_count) if reported_frame_count > 0 else None
        )
        source_video_duration_seconds = (
            reported_frame_count / reported_fps
            if source_video_reported_fps and source_video_reported_frame_count
            else None
        )

        extracted_frames: list[ExtractedFrame] = []
        next_due_milliseconds = 0.0
        interval_milliseconds = interval_seconds * 1000.0
        frame_index = 0

        while True:
            frame_was_read, frame_image = capture.read()
            if not frame_was_read:
                # End of video (or a decoding failure partway through).
                # Either way, there is no more data to read from this
                # point onward, so extraction simply stops here rather
                # than raising, as long as at least one frame was kept
                # overall (checked below).
                break

            timestamp_milliseconds = capture.get(cv2.CAP_PROP_POS_MSEC)

            if timestamp_milliseconds >= next_due_milliseconds:
                filename = FRAME_FILENAME_TEMPLATE.format(index=frame_index)
                extracted_frames.append(
                    ExtractedFrame(
                        frame_index=frame_index,
                        filename=filename,
                        timestamp_seconds=timestamp_milliseconds / 1000.0,
                        timestamp_milliseconds=timestamp_milliseconds,
                    )
                )
                frame_index += 1
                next_due_milliseconds += interval_milliseconds

                frame_path = output_dir / filename
                frame_path.parent.mkdir(parents=True, exist_ok=True)
                write_succeeded = cv2.imwrite(str(frame_path), frame_image)
                if not write_succeeded:
                    raise FrameExtractionError(
                        f"Failed to write extracted frame to {frame_path}."
                    )

        if not extracted_frames:
            raise FrameExtractionError(
                f"No frames could be extracted from {video_path}. The "
                "video may be empty, zero-length, or fail to decode any "
                "frames."
            )
    finally:
        capture.release()

    manifest = ExtractionManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        source_video_filename=video_path.name,
        source_video_size_bytes=video_path.stat().st_size,
        source_video_sha256=_sha256_of_file(video_path),
        extraction_interval_seconds=interval_seconds,
        extraction_library=f"opencv-python-headless {_opencv_python_version()}",
        source_video_duration_seconds=source_video_duration_seconds,
        source_video_reported_fps=source_video_reported_fps,
        source_video_reported_frame_count=source_video_reported_frame_count,
        frames=extracted_frames,
    )
    manifest.write_json(output_dir / MANIFEST_FILENAME)

    return manifest


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="extract-frames",
        description=(
            "Extract still frames from a local survey video at a fixed "
            "time interval (default: one frame per second), writing the "
            "frames and a traceability manifest to an output directory."
        ),
    )
    parser.add_argument(
        "video_path",
        type=Path,
        help="Path to the local video file to extract frames from.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output directory for extracted frames and manifest.json. "
            "Defaults to 'data/interim/<video filename stem>_frames/' "
            "under the current directory, this project's documented "
            "default location for derived, regenerable data."
        ),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Extraction interval in seconds (default: 1.0, i.e. one frame per second).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing extraction in the output directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point. Returns a process exit code."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    output_dir = args.output
    if output_dir is None:
        output_dir = Path("data/interim") / f"{args.video_path.stem}_frames"

    try:
        manifest = extract_frames(
            args.video_path,
            output_dir,
            interval_seconds=args.interval,
            overwrite=args.overwrite,
        )
    except FrameExtractionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(
        f"Extracted {len(manifest.frames)} frame(s) from "
        f"'{manifest.source_video_filename}' into '{output_dir}' "
        f"(interval: {manifest.extraction_interval_seconds}s). "
        f"Manifest written to '{output_dir / MANIFEST_FILENAME}'."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
