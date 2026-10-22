"""Configurable class registry for segmentation masks.

A "class registry" is just a lookup table: it says which whole numbers
(class IDs) are allowed to appear in a segmentation mask, and what each one
means (its name).

IMPORTANT — this module does NOT define CERI's real cover-type taxonomy.
CERI's actual classes are not yet known (see
docs/data_questions_for_ceri.md). The example registry shipped in
configs/cover_classes.example.toml is illustrative only, for development
and testing. See docs/decisions/0001-segmentation-as-provisional-working-
hypothesis.md for why segmentation is being used at all at this stage.

Two class IDs are always reserved, in every registry, regardless of what
real classes are configured:

- "invalid" (ID 0): the pixel should not be counted in any calculation at
  all (for example: corrupted image data, or outside the photographed
  area). Invalid pixels are not "a kind of cover" — they are excluded
  entirely.
- "unclassified" (ID 1): the pixel is valid image data, but we have no
  confident class for it. Unlike "invalid", it is still part of the
  photographed area and may be counted differently in later cover
  calculations (that logic belongs to a later milestone, not this one).

Real, configurable classes must use ID 2 or higher, so they can never
collide with the two reserved meanings above.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

# Reserved class names and their fixed IDs. These are part of every
# registry and cannot be overridden, renamed, or reused by a real class.
RESERVED_INVALID_NAME = "invalid"
RESERVED_INVALID_ID = 0

RESERVED_UNCLASSIFIED_NAME = "unclassified"
RESERVED_UNCLASSIFIED_ID = 1

# Real, configurable classes must have an ID of at least this value, so
# they never collide with the two reserved IDs above (0 and 1).
MIN_REAL_CLASS_ID = 2


class ClassRegistryError(ValueError):
    """Raised when a class registry is invalid or malformed.

    This covers problems like duplicate IDs, duplicate names, a real class
    trying to reuse a reserved ID, or a config file that doesn't have the
    structure we expect. Using one specific exception type (instead of
    letting many different errors leak out) makes it easy for callers to
    catch "something is wrong with this registry" in one place.
    """


@dataclass(frozen=True)
class ClassDefinition:
    """One class in the registry: a stable numeric ID plus a human name.

    "frozen=True" makes this immutable once created — a ClassDefinition's
    id and name can never be changed after construction, which is a good
    property for something that is supposed to act like a fixed label.
    """

    id: int
    name: str
    is_reserved: bool


@dataclass(frozen=True)
class ClassRegistry:
    """A validated, lookup-friendly collection of class definitions.

    This is the object the rest of the codebase should use to ask
    questions like "is this ID valid?" or "what does ID 2 mean?". Prefer
    building one with `ClassRegistry.from_file(...)` or
    `ClassRegistry.from_definitions(...)` rather than constructing it by
    hand, so the validation rules below are always applied.
    """

    # Mapping from class ID to its full definition. A plain dict is enough
    # here — Python dicts preserve insertion order and are fast enough for
    # a handful of classes.
    by_id: dict[int, ClassDefinition]

    def names(self) -> list[str]:
        """Return all class names, in ID order."""
        return [self.by_id[class_id].name for class_id in sorted(self.by_id)]

    def ids(self) -> list[int]:
        """Return all valid class IDs, sorted ascending."""
        return sorted(self.by_id)

    def is_valid_id(self, class_id: int) -> bool:
        """Return True if `class_id` is a registered class ID."""
        return class_id in self.by_id

    def __contains__(self, class_id: int) -> bool:
        # Lets callers write `5 in registry` instead of
        # `registry.is_valid_id(5)`, which reads naturally in a few places.
        return self.is_valid_id(class_id)

    @staticmethod
    def from_definitions(real_classes: dict[str, int]) -> ClassRegistry:
        """Build a registry from a plain {name: id} mapping of real classes.

        The two reserved classes ("invalid" and "unclassified") are added
        automatically — callers should NOT include them in `real_classes`.
        This function performs every validation rule the registry must
        satisfy; it is also used directly by unit tests, without needing a
        config file on disk.
        """
        by_id: dict[int, ClassDefinition] = {
            RESERVED_INVALID_ID: ClassDefinition(
                id=RESERVED_INVALID_ID, name=RESERVED_INVALID_NAME, is_reserved=True
            ),
            RESERVED_UNCLASSIFIED_ID: ClassDefinition(
                id=RESERVED_UNCLASSIFIED_ID, name=RESERVED_UNCLASSIFIED_NAME, is_reserved=True
            ),
        }

        seen_names: set[str] = {RESERVED_INVALID_NAME, RESERVED_UNCLASSIFIED_NAME}

        if not real_classes:
            raise ClassRegistryError(
                "A class registry must define at least one real class "
                "(in addition to the reserved 'invalid' and 'unclassified' "
                "classes). Received an empty set of real classes."
            )

        for name, class_id in real_classes.items():
            if name in (RESERVED_INVALID_NAME, RESERVED_UNCLASSIFIED_NAME):
                raise ClassRegistryError(
                    f"The class name '{name}' is reserved and cannot be "
                    "redefined as a real class."
                )

            if name in seen_names:
                raise ClassRegistryError(f"Duplicate class name: '{name}'.")

            if class_id in (RESERVED_INVALID_ID, RESERVED_UNCLASSIFIED_ID):
                raise ClassRegistryError(
                    f"Class '{name}' uses ID {class_id}, which is reserved "
                    f"for '{RESERVED_INVALID_NAME}' "
                    f"({RESERVED_INVALID_ID}) or "
                    f"'{RESERVED_UNCLASSIFIED_NAME}' "
                    f"({RESERVED_UNCLASSIFIED_ID})."
                )

            if class_id < MIN_REAL_CLASS_ID:
                raise ClassRegistryError(
                    f"Class '{name}' has ID {class_id}, but real classes "
                    f"must use an ID of {MIN_REAL_CLASS_ID} or higher "
                    "(IDs 0 and 1 are reserved)."
                )

            if class_id in by_id:
                existing_name = by_id[class_id].name
                raise ClassRegistryError(
                    f"Duplicate class ID {class_id}: already used by "
                    f"'{existing_name}', cannot also be used by '{name}'."
                )

            by_id[class_id] = ClassDefinition(id=class_id, name=name, is_reserved=False)
            seen_names.add(name)

        return ClassRegistry(by_id=by_id)

    @staticmethod
    def from_file(path: Path) -> ClassRegistry:
        """Load a class registry from a TOML configuration file.

        See configs/cover_classes.example.toml for the expected file shape
        and for important notes on what this configuration does and does
        not represent.
        """
        if not path.exists():
            raise ClassRegistryError(f"Class registry file not found: {path}")

        try:
            with path.open("rb") as config_file:
                # tomllib.load() reads a TOML file and returns a plain
                # Python dict (and nested dicts/lists for tables/arrays).
                # The file must be opened in binary mode ("rb"), which is
                # a requirement of tomllib, not an unusual choice here.
                raw_config = tomllib.load(config_file)
        except tomllib.TOMLDecodeError as error:
            raise ClassRegistryError(f"Could not parse TOML file {path}: {error}") from error

        if "classes" not in raw_config:
            raise ClassRegistryError(
                f"Config file {path} is missing a top-level [classes] table."
            )

        classes_table = raw_config["classes"]

        if not isinstance(classes_table, dict):
            raise ClassRegistryError(
                f"Config file {path}: [classes] must be a table of "
                "name = id entries."
            )

        real_classes: dict[str, int] = {}
        for name, class_id in classes_table.items():
            if not isinstance(class_id, int) or isinstance(class_id, bool):
                raise ClassRegistryError(
                    f"Config file {path}: class '{name}' must map to a "
                    f"whole number ID, got {class_id!r}."
                )
            real_classes[name] = class_id

        return ClassRegistry.from_definitions(real_classes)
