"""Unit tests for the class registry (src/eelgrass_intelligence/classes.py)."""

from pathlib import Path

import pytest

from eelgrass_intelligence.classes import (
    MIN_REAL_CLASS_ID,
    RESERVED_INVALID_ID,
    RESERVED_INVALID_NAME,
    RESERVED_UNCLASSIFIED_ID,
    RESERVED_UNCLASSIFIED_NAME,
    ClassRegistry,
    ClassRegistryError,
)

# Path to the real example config shipped with the project, so tests also
# cover the file that developers and researchers will actually look at.
EXAMPLE_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "cover_classes.example.toml"
)


def test_loading_the_example_class_registry_succeeds() -> None:
    registry = ClassRegistry.from_file(EXAMPLE_CONFIG_PATH)

    # The two reserved classes must always be present, regardless of what
    # real classes the config file defines.
    assert registry.is_valid_id(RESERVED_INVALID_ID)
    assert registry.by_id[RESERVED_INVALID_ID].name == RESERVED_INVALID_NAME
    assert registry.is_valid_id(RESERVED_UNCLASSIFIED_ID)
    assert registry.by_id[RESERVED_UNCLASSIFIED_ID].name == RESERVED_UNCLASSIFIED_NAME

    # The example file's real classes should also have loaded successfully.
    assert "example_eelgrass" in registry.names()
    assert len(registry.ids()) >= 3  # 2 reserved + at least 1 real class


def test_from_definitions_builds_a_valid_registry() -> None:
    registry = ClassRegistry.from_definitions({"sand": 2, "rock": 3})

    assert registry.ids() == [0, 1, 2, 3]
    assert registry.by_id[2].name == "sand"
    assert registry.by_id[2].is_reserved is False
    assert registry.by_id[0].is_reserved is True


def test_empty_real_classes_is_rejected() -> None:
    with pytest.raises(ClassRegistryError):
        ClassRegistry.from_definitions({})


def test_duplicate_real_class_ids_are_rejected() -> None:
    with pytest.raises(ClassRegistryError, match="Duplicate class ID"):
        ClassRegistry.from_definitions({"sand": 2, "rock": 2})


@pytest.mark.parametrize("reserved_id", [RESERVED_INVALID_ID, RESERVED_UNCLASSIFIED_ID])
def test_real_class_cannot_reuse_a_reserved_id(reserved_id: int) -> None:
    with pytest.raises(ClassRegistryError, match="reserved"):
        ClassRegistry.from_definitions({"sand": reserved_id})


@pytest.mark.parametrize("reserved_name", [RESERVED_INVALID_NAME, RESERVED_UNCLASSIFIED_NAME])
def test_real_class_cannot_reuse_a_reserved_name(reserved_name: str) -> None:
    with pytest.raises(ClassRegistryError, match="reserved"):
        ClassRegistry.from_definitions({reserved_name: 5})


def test_real_class_id_below_minimum_is_rejected() -> None:
    below_minimum_id = MIN_REAL_CLASS_ID - 1
    assert below_minimum_id in (RESERVED_INVALID_ID, RESERVED_UNCLASSIFIED_ID)

    with pytest.raises(ClassRegistryError):
        ClassRegistry.from_definitions({"sand": below_minimum_id})


def test_contains_operator_reflects_valid_ids() -> None:
    registry = ClassRegistry.from_definitions({"sand": 2})

    assert 0 in registry  # reserved "invalid"
    assert 1 in registry  # reserved "unclassified"
    assert 2 in registry  # real class "sand"
    assert 99 not in registry


def test_loading_a_missing_file_raises_a_clear_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "does_not_exist.toml"

    with pytest.raises(ClassRegistryError, match="not found"):
        ClassRegistry.from_file(missing_path)


def test_loading_a_malformed_toml_file_raises_a_clear_error(tmp_path: Path) -> None:
    malformed_path = tmp_path / "broken.toml"
    malformed_path.write_text("this is not valid TOML [[[", encoding="utf-8")

    with pytest.raises(ClassRegistryError, match="Could not parse"):
        ClassRegistry.from_file(malformed_path)


def test_loading_a_toml_file_missing_classes_table_raises_a_clear_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "no_classes_table.toml"
    path.write_text('title = "no classes table here"\n', encoding="utf-8")

    with pytest.raises(ClassRegistryError, match=r"\[classes\]"):
        ClassRegistry.from_file(path)


def test_loading_a_toml_file_with_non_integer_class_id_raises_a_clear_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bad_id.toml"
    path.write_text('[classes]\nsand = "two"\n', encoding="utf-8")

    with pytest.raises(ClassRegistryError, match="whole number ID"):
        ClassRegistry.from_file(path)
