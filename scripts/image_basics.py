"""
image_basics.py

A small, beginner-friendly exercise: open a digital image in Python and
print basic facts about it (file format, width, height, colour mode, and
pixel dimensions).

This script does NOT use any CERI data. It generates its own small sample
image on disk (if one doesn't already exist) and then inspects that image.
This keeps the exercise fully self-contained and safe to run anywhere.

How to run this (Windows): see the comment block at the very bottom of this
file, or the chat message that introduced this script.
"""

# "Path" is a convenient, modern way to work with file and folder locations
# in Python, instead of building file paths as plain text strings.
from pathlib import Path

# Pillow's module is imported as "PIL" (Python Imaging Library), even
# though the package you install is called "Pillow". "Image" is the part
# of Pillow that knows how to create, open, and read image files.
from PIL import Image

# __file__ is the path to this script itself. ".resolve()" turns it into a
# full, unambiguous path (no "..", no relative shortcuts).
# ".parent" then steps up one level, from the file to the folder it's in.
# So SCRIPT_DIR is the full path to the "scripts" folder.
SCRIPT_DIR = Path(__file__).resolve().parent

# This builds the path "scripts/sample_data" by joining SCRIPT_DIR with the
# folder name "sample_data". It does not create the folder yet.
SAMPLE_DATA_DIR = SCRIPT_DIR / "sample_data"

# This builds the full path to the actual image file we will create and
# then inspect: "scripts/sample_data/sample_image.png".
SAMPLE_IMAGE_PATH = SAMPLE_DATA_DIR / "sample_image.png"


def create_sample_image(path: Path) -> None:
    """
    Create a small, locally generated sample image and save it to disk.

    This image has NOTHING to do with CERI's real data. It is a simple
    pattern we invent ourselves, purely so this exercise has an image file
    to open and inspect without depending on the internet or on any
    outside dataset.
    """
    # "mkdir" makes the sample_data folder. "parents=True" means it will
    # also create any missing parent folders. "exist_ok=True" means: if the
    # folder already exists, don't raise an error, just carry on.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Image.new(...) creates a brand-new, blank image in memory (not yet
    # saved to a file). The arguments mean:
    #   "RGB"       -> colour mode: Red/Green/Blue, i.e. a normal colour image
    #   (300, 200)  -> size in pixels: 300 pixels wide, 200 pixels tall
    #   (30, 80, 120) -> the starting fill colour, as (Red, Green, Blue)
    #                    values from 0-255. (30, 80, 120) is a muted teal,
    #                    loosely evoking water, just for a visual touch.
    image = Image.new("RGB", (300, 200), (30, 80, 120))

    # ".save(path)" writes the image to disk at the given path. Pillow
    # looks at the file extension (".png") to decide what file format to
    # save it as. PNG is a common, lossless image format, good for a
    # simple exercise like this one.
    image.save(path)


def inspect_image(path: Path) -> None:
    """
    Open an existing image file and print basic information about it.
    """
    # Image.open(path) does NOT load the whole image into memory straight
    # away. It just opens the file and reads its header, which is enough
    # to know the format, size, and colour mode. This is why opening an
    # image is fast even for large files.
    with Image.open(path) as image:
        # "image.format" is the file format Pillow detected, e.g. "PNG",
        # "JPEG". It comes from reading the file itself, not the filename.
        file_format = image.format

        # "image.size" is a pair (width, height), in pixels. We "unpack"
        # that pair into two separate variables on one line.
        width, height = image.size

        # "image.mode" describes how colour is stored for each pixel.
        # Common values: "RGB" (red/green/blue), "L" (greyscale),
        # "RGBA" (RGB plus transparency).
        colour_mode = image.mode

        # Pixel dimensions, spelled out as a human-readable string, e.g.
        # "300 x 200 pixels". This is just width and height restated
        # together as one combined figure, which is often how image size
        # is described in practice.
        pixel_dimensions = f"{width} x {height} pixels"

        # print() displays text in the terminal. f"..." is an f-string:
        # anything inside {curly braces} gets replaced with the value of
        # that variable.
        print(f"File path:        {path}")
        print(f"File format:      {file_format}")
        print(f"Width:            {width} pixels")
        print(f"Height:           {height} pixels")
        print(f"Colour mode:      {colour_mode}")
        print(f"Pixel dimensions: {pixel_dimensions}")


def main() -> None:
    """
    The main entry point: make sure a sample image exists, then inspect it.
    """
    # "exists()" checks whether a file is already present at that path.
    # We only create a new sample image if one isn't there yet, so running
    # this script repeatedly won't keep overwriting it unnecessarily.
    if not SAMPLE_IMAGE_PATH.exists():
        print(f"No sample image found. Creating one at: {SAMPLE_IMAGE_PATH}")
        create_sample_image(SAMPLE_IMAGE_PATH)
    else:
        print(f"Using existing sample image at: {SAMPLE_IMAGE_PATH}")

    print()  # Blank line, just for readability in the terminal output.
    inspect_image(SAMPLE_IMAGE_PATH)


# This is a standard Python pattern. It means: "only run main() if this
# file is being executed directly (e.g. `python image_basics.py`), not if
# it's being imported from somewhere else." For a small standalone script
# like this, it mainly keeps things tidy and predictable.
if __name__ == "__main__":
    main()
