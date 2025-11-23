"""
Image optimization module for processing images before embedding in EPUBs.

Handles format conversion, resizing, and compression to ensure images are:
- In JPG or PNG format (converts webp and other formats)
- Appropriately sized for e-readers (1264x1680 target resolution)
- Optimized for file size without sacrificing quality
"""

import io
import logging
from typing import Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

# Target e-reader resolution (portrait mode)
COVER_MAX_WIDTH = 1264
COVER_MAX_HEIGHT = 1680

# Article images: 85% of cover dimensions
ARTICLE_MAX_WIDTH = int(COVER_MAX_WIDTH * 0.85)  # 1074
ARTICLE_MAX_HEIGHT = int(COVER_MAX_HEIGHT * 0.85)  # 1428

# Compression settings
JPG_QUALITY = 80
PNG_OPTIMIZE = True


def detect_image_format(image_data: bytes) -> Optional[str]:
    """
    Detect the actual image format from the binary data.

    Returns the format string (e.g., 'JPEG', 'PNG', 'WEBP') or None if detection fails.
    """
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            return img.format
    except Exception as e:
        logger.warning(f"Failed to detect image format: {e}")
        return None


def has_transparency(img: Image.Image) -> bool:
    """
    Check if an image has transparency/alpha channel.

    Returns True if the image has an alpha channel or transparent pixels.
    """
    # Check if image has an alpha channel
    if img.mode in ('RGBA', 'LA', 'PA'):
        return True

    # Check for transparency in palette mode
    if img.mode == 'P':
        transparency = img.info.get('transparency')
        if transparency is not None:
            return True

    return False


def resize_image(img: Image.Image, max_width: int, max_height: int) -> Image.Image:
    """
    Resize image to fit within max dimensions while maintaining aspect ratio.

    If the image is smaller than the max dimensions, it is not resized.
    Uses high-quality Lanczos resampling.
    """
    width, height = img.size

    # Skip if image is already smaller than max dimensions
    if width <= max_width and height <= max_height:
        return img

    # Calculate scaling factor to fit within dimensions
    width_ratio = max_width / width
    height_ratio = max_height / height
    scale_factor = min(width_ratio, height_ratio)

    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    logger.debug(f"Resizing image from {width}x{height} to {new_width}x{new_height}")

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def convert_svg_to_png(svg_data: bytes, max_width: int, max_height: int) -> Tuple[bytes, str]:
    """
    Convert SVG to PNG format.

    Note: This is a basic implementation that requires cairosvg.
    If cairosvg is not available, raises an ImportError.
    """
    try:
        import cairosvg
    except ImportError:
        raise ImportError(
            "cairosvg is required for SVG conversion. "
            "Install it with: uv pip install cairosvg"
        )

    # Convert SVG to PNG at the target resolution
    png_data = cairosvg.svg2png(
        bytestring=svg_data,
        output_width=max_width,
        output_height=max_height
    )

    return png_data, 'png'


def normalize_image_format(img: Image.Image, original_format: str) -> Tuple[str, str]:
    """
    Determine the appropriate output format (jpg or png) based on image characteristics.

    Returns (target_format, file_extension) tuple.
    - Images with transparency -> PNG
    - Images without transparency -> JPEG
    """
    # Always use PNG for images with transparency
    if has_transparency(img):
        return 'PNG', 'png'

    # Use JPEG for images without transparency
    return 'JPEG', 'jpg'


def optimize_image(img: Image.Image, target_format: str) -> bytes:
    """
    Compress and optimize image based on target format.

    - JPEG: 80% quality
    - PNG: optimize flag enabled, preserves transparency
    """
    output = io.BytesIO()

    if target_format == 'JPEG':
        # Convert to RGB if needed (JPEG doesn't support transparency)
        if img.mode in ('RGBA', 'LA', 'P', 'PA'):
            # Create white background for conversion
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA', 'PA') else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(output, format='JPEG', quality=JPG_QUALITY, optimize=True)
        logger.debug(f"Optimized image as JPEG with {JPG_QUALITY}% quality")

    elif target_format == 'PNG':
        # Convert palette images to RGBA for better optimization
        if img.mode == 'P':
            img = img.convert('RGBA')

        img.save(output, format='PNG', optimize=PNG_OPTIMIZE)
        logger.debug("Optimized image as PNG with transparency preserved")

    return output.getvalue()


def process_image(
    image_data: bytes,
    image_url: str,
    image_type: str = 'article'
) -> Tuple[bytes, str]:
    """
    Process an image through the full optimization pipeline.

    Args:
        image_data: Raw image bytes
        image_url: URL of the image (for logging)
        image_type: Either 'cover' or 'article' (determines max dimensions)

    Returns:
        Tuple of (processed_bytes, file_extension)

    Raises:
        Exception if processing fails
    """
    # Determine max dimensions based on image type
    if image_type == 'cover':
        max_width = COVER_MAX_WIDTH
        max_height = COVER_MAX_HEIGHT
    else:  # article
        max_width = ARTICLE_MAX_WIDTH
        max_height = ARTICLE_MAX_HEIGHT

    # Detect format
    original_format = detect_image_format(image_data)
    if not original_format:
        raise ValueError(f"Could not detect image format for {image_url}")

    logger.debug(f"Processing {image_type} image: {image_url} (format: {original_format})")

    # Handle SVG conversion
    if original_format == 'SVG':
        logger.info(f"Converting SVG to PNG: {image_url}")
        try:
            png_data, extension = convert_svg_to_png(image_data, max_width, max_height)
            return png_data, extension
        except ImportError as e:
            logger.warning(f"Cannot convert SVG (cairosvg not available): {image_url}")
            raise

    # Open image with PIL
    try:
        img = Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise ValueError(f"Failed to open image {image_url}: {e}")

    # Resize if needed
    img = resize_image(img, max_width, max_height)

    # Determine target format (jpg or png)
    target_format, extension = normalize_image_format(img, original_format)

    # Log format conversion if it changed
    if original_format.upper() not in ('JPEG', 'JPG', 'PNG'):
        logger.info(
            f"Converting {original_format} to {target_format}: {image_url}"
        )

    # Optimize and compress
    processed_data = optimize_image(img, target_format)

    # Log size reduction
    original_size = len(image_data)
    processed_size = len(processed_data)
    reduction = ((original_size - processed_size) / original_size) * 100
    logger.debug(
        f"Image processing complete: {original_size} -> {processed_size} bytes "
        f"({reduction:.1f}% reduction)"
    )

    return processed_data, extension
