"""
pixel_basics.py

A small, beginner-friendly exercise: look at individual pixel values inside
a digital image using Pillow.

This script reuses the SAME sample image created by image_basics.py
(scripts/sample_data/sample_image.png). It does not create a new image,
and it does not use any CERI data.

Before running this script, run image_basics.py at least once, so the
sample image already exists on disk.

What is a pixel?
-----------------
A digital image is really just a big grid of tiny coloured squares. Each
one of those squares is called a "pixel" (short for "picture element").
Our sample image is 300 pixels wide and 200 pixels tall, so it is a grid
of 300 x 200 = 60,000 pixels.

What do RGB values mean?
-------------------------
In "RGB" colour mode, each pixel's colour is stored as three numbers:
    Red, Green, Blue
Each number ranges from 0 to 255 (256 possible values each). Examples:
    (255, 0, 0)     -> pure red
    (0, 255, 0)     -> pure green
    (0, 0, 0)       -> black (no colour at all)
    (255, 255, 255) -> white (full of every colour)
    (30, 80, 120)   -> a muted teal (this is our sample image's colour)

How are pixel coordinates measured?
------------------------------------
Image coordinates are written as (x, y), and they work like this:
    - (0, 0) is the TOP-LEFT corner of the image.
    - x increases as you move RIGHT.
    - y increases as you move DOWN.
This is different from a maths graph, where "up" usually means increasing.
In images, "down" means increasing y. This trips up a lot of beginners,
so it's worth remembering on purpose.

How to run this (Windows): see the comment block at the very bottom of this
file, or the chat message that introduced this script.
"""

# Same imports as image_basics.py, for the same reasons: Path for file
# locations, Image for opening/reading image files with Pillow.
from pathlib import Path

from PIL import Image

# We point at the exact same sample image that image_basics.py created.
# We do NOT recreate it here — this script's job is only to read pixels,
# not to generate images.
SCRIPT_DIR = Path(__file__).resolve().parent
SAMPLE_IMAGE_PATH = SCRIPT_DIR / "sample_data" / "sample_image.png"


def print_pixel_at(image: Image.Image, x: int, y: int) -> None:
    """
    Print the RGB value of a single pixel at coordinate (x, y).
    """
    # ".getpixel((x, y))" looks up the colour stored at that exact
    # coordinate and returns it as a tuple, e.g. (30, 80, 120).
    # Note the double parentheses: getpixel takes ONE argument, which is
    # itself a pair (x, y).
    rgb_value = image.getpixel((x, y))

    print(f"Pixel at (x={x}, y={y}): RGB = {rgb_value}")


def demonstrate_in_memory_change(image: Image.Image, x: int, y: int) -> None:
    """
    Show how changing a pixel works, WITHOUT touching the original image
    file on disk.
    """
    # ".copy()" makes a brand-new, independent copy of the image in
    # memory. Any changes we make to "working_copy" below have no effect
    # whatsoever on "image" (the one we opened from disk), and no effect
    # on the sample_image.png file itself, because we never call .save()
    # on this copy.
    working_copy = image.copy()

    print("\n--- Small experiment: changing one pixel in memory ---")

    # Show the pixel's colour BEFORE we change anything.
    before_value = working_copy.getpixel((x, y))
    print(f"Before change, pixel at (x={x}, y={y}): RGB = {before_value}")

    # ".putpixel((x, y), colour)" sets the colour of a single pixel.
    # Here we set it to pure red: (255, 0, 0).
    new_colour = (255, 0, 0)
    working_copy.putpixel((x, y), new_colour)

    # Show the pixel's colour AFTER the change, proving it actually
    # updated.
    after_value = working_copy.getpixel((x, y))
    print(f"After change,  pixel at (x={x}, y={y}): RGB = {after_value}")

    print(
        "Note: this change only exists in memory, in 'working_copy'. "
        "The original sample_image.png file on disk is untouched, because "
        "we never saved 'working_copy' back to a file."
    )


def main() -> None:
    """
    Open the existing sample image and inspect some of its pixels.
    """
    # Before doing anything else, make sure the sample image actually
    # exists. If it doesn't, we tell the user what to do, instead of
    # silently creating a new one ourselves (that is image_basics.py's
    # job, not this script's).
    if not SAMPLE_IMAGE_PATH.exists():
        print(
            "No sample image found at: "
            f"{SAMPLE_IMAGE_PATH}\n"
            "Please run image_basics.py first, so the sample image is "
            "created, then run this script again."
        )
        return

    with Image.open(SAMPLE_IMAGE_PATH) as image:
        print(f"Opened image: {SAMPLE_IMAGE_PATH}")
        print(f"Image size: {image.size[0]} x {image.size[1]} pixels\n")

        # Pixel coordinate (10, 5) means: 10 pixels in from the left edge,
        # 5 pixels down from the top edge. It's deliberately close to the
        # top-left corner (0, 0), to keep the coordinate easy to picture.
        print_pixel_at(image, x=10, y=5)

        # Run the small in-memory experiment using the same coordinate,
        # so it's easy to compare with the reading above.
        demonstrate_in_memory_change(image, x=10, y=5)


# Only run main() when this file is executed directly, e.g.
# `python pixel_basics.py`, not when it's imported elsewhere.
if __name__ == "__main__":
    main()
