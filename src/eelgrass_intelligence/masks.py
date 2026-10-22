"""Segmentation mask representation and validation.

A "segmentation mask" here means: one small whole number (a class ID) for
every pixel in an image, stored as a 2D grid with the same width and
height as the image it describes. For example, a 4x3 mask is a grid with
3 rows and 4 columns of class IDs, one per pixel.

Every saved mask has TWO files on disk:

- "<name>.npy": the actual grid of class IDs, as a NumPy array file.
- "<name>.npy.meta.json": a small companion JSON file recording which
  class IDs and names were valid when this mask was saved (a snapshot of
  the ClassRegistry used), plus a schema version. This metadata file
  exists so that loading a mask with the WRONG registry — one that
  happens to use the same numeric IDs for different real-world meanings —
  is caught immediately, with a clear error, instead of silently
  mis-interpreting the mask's pixel values.

This module only represents and validates masks against a
`ClassRegistry` (see classes.py). It does NOT compute presence/absence or
percentage cover, and it does NOT produce masks from images — those are
later milestones. See docs/decisions/0001-segmentation-as-provisional-
working-hypothesis.md for why masks are being used at all at this stage,
and why that choice is provisional.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from eelgrass_intelligence.classes import ClassRegistry

# Segmentation masks are stored as small, non-negative whole numbers. This
# dtype comfortably supports thousands of distinct class IDs while using
# little memory per pixel.
MASK_DTYPE = np.uint16

# The version of the metadata file's structure (NOT the version of any
# particular class registry). Bumping this would be a deliberate,
# documented change to how metadata is stored, not something that
# changes when CERI's classes change.
MASK_METADATA_SCHEMA_VERSION = 1


class MaskError(ValueError):
    """Raised when a mask or its metadata is malformed, or fails
    validation against a ClassRegistry (wrong shape, wrong data type, an
    unregistered class ID present in the mask, or a registry that assigns
    a different meaning to one of the mask's class IDs)."""


def metadata_path_for(mask_path: Path) -> Path:
    """Return the companion metadata path for a given mask ``.npy`` path.

    For example, "scripts/sample_data/mask.npy" has metadata at
    "scripts/sample_data/mask.npy.meta.json". Keeping this in one function
    means the save and load code (and tests) always agree on where the
    metadata file lives.
    """
    return mask_path.with_name(f"{mask_path.name}.meta.json")


def _registry_classes_snapshot(registry: ClassRegistry) -> dict[int, str]:
    """Return every class ID -> name mapping currently in `registry`,
    including the reserved "invalid" and "unclassified" classes."""
    return {class_id: definition.name for class_id, definition in registry.by_id.items()}


@dataclass(frozen=True)
class SegmentationMask:
    """A validated 2D segmentation mask, tied to the registry it was
    validated against.

    Prefer building one with `SegmentationMask.from_array(...)` rather
    than constructing this directly, so validation always runs.
    """

    # A 2D NumPy array of class IDs, shape (height, width). Row 0 is the
    # top row of the image, matching how image libraries like Pillow
    # describe coordinates (see scripts/pixel_basics.py for the same
    # top-left-origin convention applied to individual pixels).
    data: np.ndarray

    # The registry this mask was validated against. Kept alongside the
    # data so a mask can always be re-checked or interpreted later without
    # needing the caller to remember which registry was used.
    registry: ClassRegistry

    @property
    def height(self) -> int:
        return int(self.data.shape[0])

    @property
    def width(self) -> int:
        return int(self.data.shape[1])

    @property
    def shape(self) -> tuple[int, int]:
        """Return (height, width), matching `data.shape`."""
        return (self.height, self.width)

    @staticmethod
    def from_array(
        data: np.ndarray,
        registry: ClassRegistry,
        expected_shape: tuple[int, int] | None = None,
    ) -> SegmentationMask:
        """Validate a raw array and wrap it as a SegmentationMask.

        Parameters
        ----------
        data:
            A 2D array of class IDs, shape (height, width).
        registry:
            The ClassRegistry every ID in `data` must belong to.
        expected_shape:
            If given, as (height, width), the array's shape must match
            exactly. Use this when a mask is supposed to correspond to a
            specific image, so a mismatched mask is rejected explicitly
            instead of silently misaligning with the image it's meant to
            describe.

        Raises
        ------
        MaskError
            If `data` is not 2D, is empty, does not match
            `expected_shape` (when given), or contains any class ID not
            present in `registry`.
        """
        if not isinstance(data, np.ndarray):
            raise MaskError(f"Mask data must be a NumPy array, got {type(data).__name__}.")

        if data.ndim != 2:
            raise MaskError(
                f"Mask data must be 2-dimensional (height, width), got "
                f"{data.ndim} dimension(s) with shape {data.shape}."
            )

        height, width = data.shape
        if height == 0 or width == 0:
            raise MaskError(f"Mask must not be empty, got shape {data.shape}.")

        if expected_shape is not None and (height, width) != expected_shape:
            raise MaskError(
                f"Mask shape {(height, width)} does not match the expected "
                f"shape {expected_shape}."
            )

        # Reject non-whole-number data (e.g. floats) before even looking
        # at the values, since a class ID can never be fractional.
        if not np.issubdtype(data.dtype, np.integer):
            raise MaskError(
                f"Mask data must contain whole numbers (an integer dtype), "
                f"got dtype {data.dtype}."
            )

        if np.any(data < 0):
            raise MaskError("Mask contains negative class IDs, which are never valid.")

        # np.unique() returns every distinct value that appears in the
        # array. We compare that small set of distinct IDs against the
        # registry, rather than checking every single pixel one at a
        # time, which is both simpler and faster.
        unique_ids = np.unique(data)
        unknown_ids = [int(class_id) for class_id in unique_ids if class_id not in registry]
        if unknown_ids:
            known_ids = registry.ids()
            raise MaskError(
                f"Mask contains class ID(s) not present in the registry: "
                f"{unknown_ids}. Known IDs are: {known_ids}."
            )

        # Store the data using our standard dtype, so two masks built from
        # different source dtypes (e.g. int32 vs int64) still compare and
        # save/load consistently.
        normalized_data = data.astype(MASK_DTYPE)

        return SegmentationMask(data=normalized_data, registry=registry)

    def save(self, path: Path) -> None:
        """Save this mask to disk as a NumPy ``.npy`` file, plus a
        companion ``.meta.json`` metadata file recording the schema
        version and the full class ID -> name mapping of the registry
        this mask was validated against.

        The metadata file lets `load_mask` detect, with a clear error, a
        registry that assigns a different real-world meaning to one of
        this mask's class IDs than the registry used here.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, self.data)

        metadata = {
            "schema_version": MASK_METADATA_SCHEMA_VERSION,
            # JSON object keys must be strings, so class IDs are written
            # as strings here and converted back to int on load.
            "classes": {
                str(class_id): name
                for class_id, name in _registry_classes_snapshot(self.registry).items()
            },
        }
        metadata_path = metadata_path_for(path)
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")


def _load_and_validate_metadata(metadata_path: Path, registry: ClassRegistry) -> None:
    """Read, parse, and validate a mask's companion metadata file.

    Raises
    ------
    MaskError
        If the metadata file is missing, unreadable, not valid JSON, not
        shaped as expected, uses an unsupported schema version, or
        assigns a different name to a class ID that `registry` also
        defines (a sign the wrong registry is being used to read this
        mask).
    """
    if not metadata_path.exists():
        raise MaskError(
            f"Mask metadata file not found: {metadata_path}. Every mask "
            "saved by this project has a companion '<name>.npy.meta.json' "
            "file; a mask without one cannot be safely interpreted, "
            "because we would not know which class IDs its registry used."
        )

    try:
        raw_text = metadata_path.read_text(encoding="utf-8")
    except OSError as error:
        raise MaskError(f"Could not read mask metadata file {metadata_path}: {error}") from error

    try:
        metadata = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise MaskError(
            f"Mask metadata file {metadata_path} is not valid JSON: {error}"
        ) from error

    if not isinstance(metadata, dict):
        raise MaskError(f"Mask metadata file {metadata_path} must contain a JSON object.")

    if "schema_version" not in metadata:
        raise MaskError(f"Mask metadata file {metadata_path} is missing 'schema_version'.")

    schema_version = metadata["schema_version"]
    if schema_version != MASK_METADATA_SCHEMA_VERSION:
        raise MaskError(
            f"Mask metadata file {metadata_path} has schema_version "
            f"{schema_version!r}, but this version of the project only "
            f"supports schema_version {MASK_METADATA_SCHEMA_VERSION}."
        )

    if "classes" not in metadata or not isinstance(metadata["classes"], dict):
        raise MaskError(
            f"Mask metadata file {metadata_path} is missing a valid "
            "'classes' object mapping class IDs to names."
        )

    saved_classes: dict[int, str] = {}
    for raw_id, name in metadata["classes"].items():
        try:
            class_id = int(raw_id)
        except (TypeError, ValueError) as error:
            raise MaskError(
                f"Mask metadata file {metadata_path} has a non-numeric "
                f"class ID key: {raw_id!r}."
            ) from error

        if not isinstance(name, str):
            raise MaskError(
                f"Mask metadata file {metadata_path} has a non-text class "
                f"name for ID {class_id}: {name!r}."
            )

        saved_classes[class_id] = name

    # Only compare IDs that appear in BOTH the saved metadata and the
    # supplied registry. A registry that has grown since this mask was
    # saved (e.g. a new class added with a brand-new ID) is fine — that
    # is not a change in meaning for any ID this mask actually used.
    # What must be rejected is an ID that both sides define, but with a
    # different name, since that means the same number now means
    # something different.
    expected_classes = _registry_classes_snapshot(registry)
    shared_ids = set(saved_classes) & set(expected_classes)
    mismatches = [
        f"ID {class_id}: saved as {saved_classes[class_id]!r}, "
        f"supplied registry has {expected_classes[class_id]!r}"
        for class_id in sorted(shared_ids)
        if saved_classes[class_id] != expected_classes[class_id]
    ]
    if mismatches:
        raise MaskError(
            "Mask metadata does not match the supplied class registry: "
            "the registry used to load this mask assigns a different "
            "meaning to at least one of its class IDs than the registry "
            "used to save it. This mask must not be interpreted with "
            "this registry. Mismatches:\n" + "\n".join(mismatches)
        )


def load_mask(
    path: Path,
    registry: ClassRegistry,
    expected_shape: tuple[int, int] | None = None,
) -> SegmentationMask:
    """Load a mask previously saved with `SegmentationMask.save`, and
    validate both its companion metadata and its pixel data against
    `registry` (and `expected_shape`, if given).

    Raises
    ------
    MaskError
        If the mask file or its metadata file is missing or unreadable,
        if the metadata is malformed, if the metadata's class IDs mean
        something different under `registry` (see
        `_load_and_validate_metadata`), or if the mask's pixel data fails
        validation against the registry (see
        `SegmentationMask.from_array`).
    """
    if not path.exists():
        raise MaskError(f"Mask file not found: {path}")

    _load_and_validate_metadata(metadata_path_for(path), registry)

    try:
        # allow_pickle=False is important: it means this function can only
        # ever load plain numeric array data, never arbitrary Python
        # objects, which keeps loading a mask file safe even if the file
        # came from an untrusted source.
        raw_data = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as error:
        raise MaskError(f"Could not read mask file {path}: {error}") from error

    return SegmentationMask.from_array(raw_data, registry, expected_shape=expected_shape)
