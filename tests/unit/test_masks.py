"""Unit tests for segmentation masks (src/eelgrass_intelligence/masks.py)."""

import json
from pathlib import Path

import numpy as np
import pytest

from eelgrass_intelligence.classes import (
    RESERVED_INVALID_ID,
    RESERVED_UNCLASSIFIED_ID,
    ClassRegistry,
)
from eelgrass_intelligence.masks import (
    MASK_METADATA_SCHEMA_VERSION,
    MaskError,
    SegmentationMask,
    load_mask,
    metadata_path_for,
)


@pytest.fixture
def registry() -> ClassRegistry:
    """A small, fixed registry used across most tests in this file."""
    return ClassRegistry.from_definitions({"sand": 2, "rock": 3})


def test_valid_mask_is_accepted(registry: ClassRegistry) -> None:
    data = np.array([[0, 1, 2], [2, 3, 0]], dtype=np.int32)

    mask = SegmentationMask.from_array(data, registry)

    assert mask.height == 2
    assert mask.width == 3
    assert mask.shape == (2, 3)
    # The original pixel values must be preserved exactly.
    assert mask.data.tolist() == [[0, 1, 2], [2, 3, 0]]


def test_mask_rejects_unknown_class_ids(registry: ClassRegistry) -> None:
    data = np.array([[0, 1], [2, 99]], dtype=np.int32)  # 99 is not registered

    with pytest.raises(MaskError, match="not present in the registry"):
        SegmentationMask.from_array(data, registry)


def test_mask_rejects_wrong_expected_shape(registry: ClassRegistry) -> None:
    data = np.zeros((2, 3), dtype=np.int32)

    with pytest.raises(MaskError, match="does not match the expected shape"):
        SegmentationMask.from_array(data, registry, expected_shape=(5, 5))


def test_mask_accepts_matching_expected_shape(registry: ClassRegistry) -> None:
    data = np.zeros((2, 3), dtype=np.int32)

    mask = SegmentationMask.from_array(data, registry, expected_shape=(2, 3))

    assert mask.shape == (2, 3)


def test_mask_rejects_non_2d_array(registry: ClassRegistry) -> None:
    one_dimensional = np.array([0, 1, 2], dtype=np.int32)

    with pytest.raises(MaskError, match="2-dimensional"):
        SegmentationMask.from_array(one_dimensional, registry)

    three_dimensional = np.zeros((2, 2, 2), dtype=np.int32)

    with pytest.raises(MaskError, match="2-dimensional"):
        SegmentationMask.from_array(three_dimensional, registry)


def test_mask_rejects_empty_array(registry: ClassRegistry) -> None:
    empty = np.zeros((0, 0), dtype=np.int32)

    with pytest.raises(MaskError, match="must not be empty"):
        SegmentationMask.from_array(empty, registry)


def test_mask_rejects_non_integer_dtype(registry: ClassRegistry) -> None:
    float_data = np.zeros((2, 2), dtype=np.float32)

    with pytest.raises(MaskError, match="whole numbers"):
        SegmentationMask.from_array(float_data, registry)


def test_mask_rejects_negative_values(registry: ClassRegistry) -> None:
    data = np.array([[0, -1], [2, 3]], dtype=np.int32)

    with pytest.raises(MaskError, match="negative"):
        SegmentationMask.from_array(data, registry)


def test_mask_rejects_non_array_input(registry: ClassRegistry) -> None:
    with pytest.raises(MaskError, match="NumPy array"):
        SegmentationMask.from_array([[0, 1], [2, 3]], registry)  # type: ignore[arg-type]


def test_save_and_reload_preserves_shape_and_values(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    original_data = np.array(
        [
            [RESERVED_INVALID_ID, RESERVED_UNCLASSIFIED_ID, 2],
            [3, 2, RESERVED_INVALID_ID],
        ],
        dtype=np.int32,
    )
    mask = SegmentationMask.from_array(original_data, registry)

    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    reloaded = load_mask(save_path, registry)

    assert reloaded.shape == mask.shape
    assert reloaded.data.tolist() == mask.data.tolist()


def test_save_and_reload_keeps_invalid_and_unclassified_distinguishable(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    # One pixel of each reserved class, in known, different positions.
    original_data = np.array(
        [[RESERVED_INVALID_ID, RESERVED_UNCLASSIFIED_ID]],
        dtype=np.int32,
    )
    mask = SegmentationMask.from_array(original_data, registry)

    save_path = tmp_path / "mask.npy"
    mask.save(save_path)
    reloaded = load_mask(save_path, registry)

    # After the round trip, the two reserved pixels must still be
    # different from each other, and still equal to their original,
    # distinct reserved IDs — not merged or confused in any way.
    assert int(reloaded.data[0, 0]) == RESERVED_INVALID_ID
    assert int(reloaded.data[0, 1]) == RESERVED_UNCLASSIFIED_ID
    assert reloaded.data[0, 0] != reloaded.data[0, 1]


def test_load_mask_rejects_mismatched_expected_shape_after_reload(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    mask = SegmentationMask.from_array(np.zeros((2, 2), dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    with pytest.raises(MaskError, match="does not match the expected shape"):
        load_mask(save_path, registry, expected_shape=(9, 9))


def test_load_mask_missing_file_raises_a_clear_error(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    missing_path = tmp_path / "does_not_exist.npy"

    with pytest.raises(MaskError, match="not found"):
        load_mask(missing_path, registry)


def test_load_mask_rejects_a_malformed_file(tmp_path: Path, registry: ClassRegistry) -> None:
    malformed_path = tmp_path / "not_actually_npy.npy"
    malformed_path.write_text("this is not a numpy array file", encoding="utf-8")

    # Give it a valid, matching metadata file, so this test is isolated to
    # checking the .npy array file itself, not the metadata check that
    # now runs first in load_mask().
    metadata_path_for(malformed_path).write_text(
        json.dumps(
            {
                "schema_version": MASK_METADATA_SCHEMA_VERSION,
                "classes": {"0": "invalid", "1": "unclassified", "2": "sand", "3": "rock"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MaskError, match="Could not read mask file"):
        load_mask(malformed_path, registry)


def test_load_mask_rejects_file_with_unknown_class_ids(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    # Save a mask using a *different*, more permissive registry, then try
    # to load it back using the stricter fixture registry, to prove
    # validation is re-applied on load rather than trusted blindly.
    permissive_registry = ClassRegistry.from_definitions({"sand": 2, "mystery": 50})
    data = np.array([[50]], dtype=np.int32)
    mask = SegmentationMask.from_array(data, permissive_registry)

    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    with pytest.raises(MaskError, match="not present in the registry"):
        load_mask(save_path, registry)


# --- Companion metadata file tests ---


def test_save_writes_a_metadata_file_alongside_the_mask(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    mask = SegmentationMask.from_array(np.array([[2, 3]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"

    mask.save(save_path)

    metadata_path = metadata_path_for(save_path)
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["schema_version"] == MASK_METADATA_SCHEMA_VERSION
    # All four classes (2 reserved + 2 real) must be recorded, keyed by
    # their class ID (as a string, since JSON object keys are always
    # strings) and mapped to the exact name the registry gave them.
    assert metadata["classes"] == {
        "0": "invalid",
        "1": "unclassified",
        "2": "sand",
        "3": "rock",
    }


def test_matching_registry_loads_successfully(tmp_path: Path, registry: ClassRegistry) -> None:
    mask = SegmentationMask.from_array(np.array([[2, 3]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    # A freshly built registry with the exact same names and IDs (not the
    # same Python object) must still be accepted.
    same_meaning_registry = ClassRegistry.from_definitions({"sand": 2, "rock": 3})
    reloaded = load_mask(save_path, same_meaning_registry)

    assert reloaded.data.tolist() == [[2, 3]]


def test_registry_with_new_additional_classes_still_loads(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    # A registry that has grown since the mask was saved (a brand-new ID
    # that didn't exist before) must still be accepted — this is not a
    # change in meaning for any ID the mask actually uses.
    mask = SegmentationMask.from_array(np.array([[2]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    grown_registry = ClassRegistry.from_definitions({"sand": 2, "rock": 3, "coral": 4})

    reloaded = load_mask(save_path, grown_registry)

    assert reloaded.data.tolist() == [[2]]


def test_registry_that_renames_a_shared_id_is_rejected(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    # Same ID (2), but it now means something different ("algae" instead
    # of "sand"). This is exactly the dangerous case metadata validation
    # exists to catch: the pixel data would load "successfully" but be
    # silently misinterpreted if we didn't check this.
    mask = SegmentationMask.from_array(np.array([[2]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    conflicting_registry = ClassRegistry.from_definitions({"algae": 2, "rock": 3})

    with pytest.raises(MaskError, match="does not match the supplied class registry"):
        load_mask(save_path, conflicting_registry)


def test_missing_metadata_file_raises_a_clear_error(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    mask = SegmentationMask.from_array(np.array([[2]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    # Remove the metadata file, leaving only the raw .npy array behind.
    metadata_path_for(save_path).unlink()

    with pytest.raises(MaskError, match="metadata file not found"):
        load_mask(save_path, registry)


def test_malformed_metadata_json_raises_a_clear_error(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    mask = SegmentationMask.from_array(np.array([[2]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    metadata_path_for(save_path).write_text("this is not valid JSON {{{", encoding="utf-8")

    with pytest.raises(MaskError, match="not valid JSON"):
        load_mask(save_path, registry)


def test_metadata_missing_schema_version_raises_a_clear_error(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    mask = SegmentationMask.from_array(np.array([[2]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    metadata_path_for(save_path).write_text(
        json.dumps({"classes": {"2": "sand"}}), encoding="utf-8"
    )

    with pytest.raises(MaskError, match="missing 'schema_version'"):
        load_mask(save_path, registry)


def test_metadata_unsupported_schema_version_raises_a_clear_error(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    mask = SegmentationMask.from_array(np.array([[2]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    metadata_path_for(save_path).write_text(
        json.dumps({"schema_version": 999, "classes": {"2": "sand"}}), encoding="utf-8"
    )

    with pytest.raises(MaskError, match="schema_version"):
        load_mask(save_path, registry)


def test_metadata_missing_classes_key_raises_a_clear_error(
    tmp_path: Path, registry: ClassRegistry
) -> None:
    mask = SegmentationMask.from_array(np.array([[2]], dtype=np.int32), registry)
    save_path = tmp_path / "mask.npy"
    mask.save(save_path)

    metadata_path_for(save_path).write_text(
        json.dumps({"schema_version": MASK_METADATA_SCHEMA_VERSION}), encoding="utf-8"
    )

    with pytest.raises(MaskError, match="valid 'classes' object"):
        load_mask(save_path, registry)
