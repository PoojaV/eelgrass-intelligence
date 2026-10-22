"""
compare_images.py

A small, beginner-friendly exercise: open several images and compare their
basic properties side by side (filename, width, height, format, colour
mode).

This script reuses the EXISTING sample image created by image_basics.py
(scripts/sample_data/sample_image.png) without changing it, and creates
two additional synthetic sample images (if they don't already exist yet)
with different sizes and solid colours, so there is something meaningful
to compare.

None of these images come from CERI. They are all generated locally,
purely for learning purposes.

Before running this script, it's a good idea to have already run
image_basics.py at least once, so sample_image.png exists. If it doesn't
exist yet, this script will tell you to run image_basics.py first, rather
than creating it itself — creating that particular file is image_basics.py's
job, not this script's.

How to run this (Windows): see the comment block at the very bottom of this
file.
"""

from pathlib import Path

from PIL import Image

# Same pattern as the earlier scripts: find the "scripts" folder this file
# lives in, then point at the shared "sample_data" folder inside it.
SCRIPT_DIR = Path(__file__).resolve().parent
SAMPLE_DATA_DIR = SCRIPT_DIR / "sample_data"

# The image reused from image_basics.py. We only ever read this one, never
# create or overwrite it here.
EXISTING_SAMPLE_IMAGE_PATH = SAMPLE_DATA_DIR / "sample_image.png"

# Two new sample images, each with a different size and colour, so we have
# something interesting to compare. "size" is (width, height) in pixels.
# "colour" is an (R, G, B) triplet, each value 0-255.
WIDE_SAMPLE_IMAGE_PATH = SAMPLE_DATA_DIR / "sample_image_wide.png"
WIDE_SAMPLE_SIZE = (400, 100)
WIDE_SAMPLE_COLOUR = (194, 178, 128)  # sandy tan, loosely evokes seafloor

SMALL_SAMPLE_IMAGE_PATH = SAMPLE_DATA_DIR / "sample_image_small.png"
SMALL_SAMPLE_SIZE = (150, 150)
SMALL_SAMPLE_COLOUR = (34, 95, 60)  # muted green, loosely evokes eelgrass


def ensure_sample_image(path: Path, size: tuple[int, int], colour: tuple[int, int, int]) -> None:
    """
    Make sure an image file exists at "path". If it doesn't exist yet,
    create a new, solid-colour image with the given size and colour and
    save it there. If it already exists, do nothing, so we never
    overwrite an image that's already on disk.
    """
    if path.exists():
        return

    # Make sure the sample_data folder exists before saving into it.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Image.new("RGB", size, colour) creates a blank image in memory,
    # filled entirely with one solid colour. ".save(path)" then writes it
    # to disk; Pillow uses the ".png" file extension to pick the file
    # format automatically.
    image = Image.new("RGB", size, colour)
    image.save(path)


def print_image_properties(path: Path) -> None:
    """
    Open an image file and print its filename, width, height, format, and
    colour mode, in a simple aligned layout.
    """
    # Image.open() reads just enough of the file to know its format and
    # size, without loading every pixel into memory.
    with Image.open(path) as image:
        width, height = image.size

        # ".name" on a Path gives just the filename (e.g.
        # "sample_image.png"), without the rest of the folder path. This
        # keeps the printed output short and easy to read.
        print(f"Filename:    {path.name}")
        print(f"Width:       {width} pixels")
        print(f"Height:      {height} pixels")
        print(f"Format:      {image.format}")
        print(f"Colour mode: {image.mode}")


def main() -> None:
    """
    Make sure all three sample images exist, then print and compare their
    properties, one after another.
    """
    if not EXISTING_SAMPLE_IMAGE_PATH.exists():
        print(
            "No sample image found at: "
            f"{EXISTING_SAMPLE_IMAGE_PATH}\n"
            "Please run image_basics.py first, so the sample image is "
            "created, then run this script again."
        )
        return

    # Create the two new sample images, only if they don't already exist.
    ensure_sample_image(WIDE_SAMPLE_IMAGE_PATH, WIDE_SAMPLE_SIZE, WIDE_SAMPLE_COLOUR)
    ensure_sample_image(SMALL_SAMPLE_IMAGE_PATH, SMALL_SAMPLE_SIZE, SMALL_SAMPLE_COLOUR)

    # List all three images together, so the loop below can print each
    # one's properties using the same code, instead of repeating ourselves
    # three times.
    all_sample_image_paths = [
        EXISTING_SAMPLE_IMAGE_PATH,
        WIDE_SAMPLE_IMAGE_PATH,
        SMALL_SAMPLE_IMAGE_PATH,
    ]

    for index, path in enumerate(all_sample_image_paths, start=1):
        print(f"--- Image {index} of {len(all_sample_image_paths)} ---")
        print_image_properties(path)
        print()  # Blank line between images, for readability.


if __name__ == "__main__":
    main()
