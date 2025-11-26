"""Automatic cover generation from article thumbnails."""

import io
import logging
import platform
from typing import Optional, List, Tuple
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .image_optimizer import process_image

logger = logging.getLogger(__name__)

# Cover dimensions (standard e-reader portrait)
COVER_WIDTH = 1264
COVER_HEIGHT = 1680

# Banner height at bottom
BANNER_HEIGHT = 200

# Layout configurations (rows, cols)
# Designed for landscape thumbnails on portrait cover (1264x1680)
LAYOUTS = {
    1: (1, 1),  # 1x1 (single image, full cover)
    2: (2, 1),  # 2x1 (horizontal stacked, landscape cells: 1264x790)
    3: (2, 2),  # 2x2 (use 3 slots, leave one empty, cells: 632x790 portrait)
    4: (2, 2),  # 2x2 (full grid, cells: 632x790 portrait)
    5: (3, 2),  # 3x2 (use 5 slots, landscape cells: 632x526)
    6: (3, 2),  # 3x2 (full grid, landscape cells: 632x526)
}


class CoverGenerator:
    """Generates EPUB covers from thumbnails or text."""

    def __init__(self):
        self._font_cache = {}

    async def generate_from_thumbnails(
        self,
        thumbnail_urls: List[str],
        title: str,
        author: Optional[str],
        fetcher,
        fallback_to_text: bool = True
    ) -> Tuple[bytes, str]:
        """
        Generate cover from thumbnail URLs.

        Args:
            thumbnail_urls: List of image URLs to use for mosaic
            title: Publication title for banner
            author: Author/publisher name (optional)
            fetcher: CachedFetcher instance for downloading images
            fallback_to_text: If True, fall back to text cover when insufficient thumbnails

        Returns:
            Tuple of (image_bytes, extension)

        Raises:
            Exception: If cover generation fails and fallback_to_text is False
        """
        logger.info(f"Generating cover from {len(thumbnail_urls)} thumbnails")

        # Download and process thumbnails
        images = await self._download_thumbnails(thumbnail_urls, fetcher)

        logger.info(f"Successfully downloaded {len(images)}/{len(thumbnail_urls)} thumbnails")

        # Check if we have enough images
        if len(images) < 2 and fallback_to_text:
            logger.info("Insufficient thumbnails (<2), falling back to text cover")
            return self.generate_text_cover(title, author, date=datetime.now().strftime("%B %Y"))

        if len(images) == 0:
            if fallback_to_text:
                return self.generate_text_cover(title, author, date=datetime.now().strftime("%B %Y"))
            else:
                raise Exception("No thumbnails available for cover generation")

        # Create mosaic
        cover_image = self._create_mosaic(images, title, author)

        # Convert to bytes
        output = io.BytesIO()
        cover_image.save(output, format='JPEG', quality=80, optimize=True)
        image_bytes = output.getvalue()

        logger.info(f"Generated mosaic cover ({len(image_bytes)} bytes)")
        return (image_bytes, 'jpg')

    def generate_text_cover(
        self,
        title: str,
        author: Optional[str] = None,
        date: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """
        Generate text-only cover with gradient background.

        Args:
            title: Publication title
            author: Author/publisher name (optional)
            date: Date string (optional, shown at bottom)

        Returns:
            Tuple of (image_bytes, extension)
        """
        logger.info(f"Generating text-only cover for '{title}'")

        # Create gradient background
        cover = self._create_gradient_background(COVER_WIDTH, COVER_HEIGHT)

        # Draw text
        draw = ImageDraw.Draw(cover)

        # Calculate text positions (centered vertically)
        center_x = COVER_WIDTH // 2
        center_y = COVER_HEIGHT // 2

        # Title
        title_font = self._get_font(72, bold=True)
        title_lines = self._wrap_text(title, title_font, COVER_WIDTH - 100)

        # Calculate total height of text block
        title_height = len(title_lines) * 85
        author_height = 60 if author else 0
        date_height = 50 if date else 0
        total_height = title_height + author_height + date_height

        # Start y position (centered)
        y = center_y - (total_height // 2)

        # Draw title (white text)
        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            x = center_x - (text_width // 2)
            draw.text((x, y), line, font=title_font, fill='white')
            y += 85

        # Draw author
        if author:
            y += 20  # Spacing
            author_font = self._get_font(48, bold=False)
            bbox = draw.textbbox((0, 0), author, font=author_font)
            text_width = bbox[2] - bbox[0]
            x = center_x - (text_width // 2)
            draw.text((x, y), author, font=author_font, fill='white')
            y += 60

        # Draw date at bottom
        if date:
            date_font = self._get_font(32, bold=False)
            bbox = draw.textbbox((0, 0), date, font=date_font)
            text_width = bbox[2] - bbox[0]
            x = center_x - (text_width // 2)
            y = COVER_HEIGHT - 100
            draw.text((x, y), date, font=date_font, fill='white')

        # Convert to bytes
        output = io.BytesIO()
        cover.save(output, format='JPEG', quality=80, optimize=True)
        image_bytes = output.getvalue()

        logger.info(f"Generated text cover ({len(image_bytes)} bytes)")
        return (image_bytes, 'jpg')

    async def _download_thumbnails(
        self,
        thumbnail_urls: List[str],
        fetcher
    ) -> List[Image.Image]:
        """
        Download and process thumbnails into PIL Images.

        Args:
            thumbnail_urls: List of image URLs
            fetcher: CachedFetcher instance

        Returns:
            List of PIL Image objects (successfully downloaded only)
        """
        images = []

        for url in thumbnail_urls:
            try:
                # Download image (fetch_binary returns tuple: data, final_url)
                image_data, _ = await fetcher.fetch_binary(url, context="cover")

                # Process image (resize, optimize)
                processed_data, ext = process_image(image_data, url, image_type='cover')

                # Convert to PIL Image
                img = Image.open(io.BytesIO(processed_data))

                # Ensure RGB mode (no alpha for JPEG)
                if img.mode != 'RGB':
                    if img.mode == 'RGBA' or img.mode == 'LA' or img.mode == 'PA':
                        # Create white background
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA', 'PA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    else:
                        img = img.convert('RGB')

                images.append(img)
                logger.debug(f"Downloaded thumbnail: {url}")

            except Exception as e:
                logger.warning(f"Failed to download thumbnail {url}: {e}")
                continue

        return images

    def _create_mosaic(
        self,
        images: List[Image.Image],
        title: str,
        author: Optional[str]
    ) -> Image.Image:
        """
        Create mosaic layout from images with title banner.

        Args:
            images: List of PIL Images
            title: Publication title
            author: Author/publisher name (optional)

        Returns:
            PIL Image of the mosaic cover
        """
        # Determine layout
        num_images = min(len(images), 6)
        rows, cols = LAYOUTS.get(num_images, (2, 3))

        logger.debug(f"Creating {rows}x{cols} mosaic for {num_images} images")

        # Calculate cell dimensions (reserve space for banner)
        content_height = COVER_HEIGHT - BANNER_HEIGHT
        cell_width = COVER_WIDTH // cols
        cell_height = content_height // rows

        # Create canvas
        canvas = Image.new('RGB', (COVER_WIDTH, COVER_HEIGHT), (255, 255, 255))

        # Paste images into grid
        for idx, img in enumerate(images[:num_images]):
            # Calculate position
            row = idx // cols
            col = idx % cols
            x = col * cell_width
            y = row * cell_height

            # Resize image to fill cell (crop to fit)
            resized_img = self._resize_and_crop(img, cell_width, cell_height)

            # Paste onto canvas
            canvas.paste(resized_img, (x, y))

        # Add banner at bottom
        canvas_with_banner = self._add_text_banner(canvas, title, author)

        return canvas_with_banner

    def _resize_and_crop(self, img: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """
        Resize and center-crop image to fill target dimensions.

        Args:
            img: PIL Image to resize
            target_width: Target width
            target_height: Target height

        Returns:
            Resized and cropped PIL Image
        """
        # Calculate aspect ratios
        img_aspect = img.width / img.height
        target_aspect = target_width / target_height

        if img_aspect > target_aspect:
            # Image is wider - fit height, crop width
            new_height = target_height
            new_width = int(target_height * img_aspect)
        else:
            # Image is taller - fit width, crop height
            new_width = target_width
            new_height = int(target_width / img_aspect)

        # Resize
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Crop to target dimensions (center crop)
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        cropped = resized.crop((left, top, right, bottom))

        return cropped

    def _create_gradient_background(self, width: int, height: int) -> Image.Image:
        """
        Create gradient background (top-to-bottom color transition).

        Args:
            width: Image width
            height: Image height

        Returns:
            PIL Image with gradient
        """
        # Create gradient from blue to purple
        top_color = (41, 128, 185)  # Blue
        bottom_color = (142, 68, 173)  # Purple

        gradient = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(gradient)

        # Draw gradient line by line
        for y in range(height):
            # Interpolate color
            ratio = y / height
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)

            draw.line([(0, y), (width, y)], fill=(r, g, b))

        return gradient

    def _add_text_banner(
        self,
        base_image: Image.Image,
        title: str,
        author: Optional[str]
    ) -> Image.Image:
        """
        Add text banner at bottom of image.

        Args:
            base_image: Base PIL Image
            title: Publication title
            author: Author/publisher name (optional, shown as generation date if provided)

        Returns:
            PIL Image with banner added
        """
        # Create semi-transparent overlay
        overlay = Image.new('RGBA', base_image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw semi-transparent black rectangle at bottom
        banner_top = COVER_HEIGHT - BANNER_HEIGHT
        draw.rectangle(
            [(0, banner_top), (COVER_WIDTH, COVER_HEIGHT)],
            fill=(0, 0, 0, 200)  # Black with 200/255 opacity
        )

        # Convert base image to RGBA for compositing
        if base_image.mode != 'RGBA':
            base_rgba = base_image.convert('RGBA')
        else:
            base_rgba = base_image.copy()

        # Composite overlay
        result = Image.alpha_composite(base_rgba, overlay)

        # Draw text on result
        draw = ImageDraw.Draw(result)

        # Title (smaller size to fit better)
        title_font = self._get_font(72, bold=True)
        title_truncated = self._truncate_text(title, title_font, COVER_WIDTH - 40)

        bbox = draw.textbbox((0, 0), title_truncated, font=title_font)
        text_width = bbox[2] - bbox[0]
        x = (COVER_WIDTH - text_width) // 2
        y = banner_top + 25

        draw.text((x, y), title_truncated, font=title_font, fill='white')

        # Generation date/time
        from datetime import datetime
        date_text = datetime.now().strftime("%B %d, %Y · %H:%M")

        date_font = self._get_font(36, bold=False)
        date_truncated = self._truncate_text(date_text, date_font, COVER_WIDTH - 40)

        bbox = draw.textbbox((0, 0), date_truncated, font=date_font)
        text_width = bbox[2] - bbox[0]
        x = (COVER_WIDTH - text_width) // 2
        y = banner_top + 25 + 72 + 30  # Below title with 50px spacing

        draw.text((x, y), date_truncated, font=date_font, fill='white')

        # Convert back to RGB for JPEG
        final = result.convert('RGB')

        return final

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """
        Get system font or fallback to default.

        Args:
            size: Font size in points
            bold: Whether to use bold variant

        Returns:
            PIL ImageFont object
        """
        cache_key = (size, bold)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        # Try system fonts by platform
        system = platform.system()
        font_names = []

        if system == 'Windows':
            if bold:
                font_names = ['arialbd.ttf', 'segoeuib.ttf', 'calibrib.ttf']
            else:
                font_names = ['arial.ttf', 'segoeui.ttf', 'calibri.ttf']
        elif system == 'Darwin':  # macOS
            if bold:
                font_names = ['Helvetica-Bold', 'SF-Pro-Display-Bold.otf', 'Arial Bold']
            else:
                font_names = ['Helvetica', 'SF-Pro-Display-Regular.otf', 'Arial']
        else:  # Linux/other
            if bold:
                font_names = ['LiberationSans-Bold.ttf', 'DejaVuSans-Bold.ttf', 'FreeSansBold.ttf']
            else:
                font_names = ['LiberationSans-Regular.ttf', 'DejaVuSans.ttf', 'FreeSans.ttf']

        # Try each font
        font = None
        for font_name in font_names:
            try:
                font = ImageFont.truetype(font_name, size)
                logger.debug(f"Loaded font: {font_name} (size={size}, bold={bold})")
                break
            except (OSError, IOError):
                continue

        # Fallback to default
        if font is None:
            logger.debug(f"Using default font (size={size}, bold={bold})")
            font = ImageFont.load_default()

        self._font_cache[cache_key] = font
        return font

    def _truncate_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
        """
        Truncate text with ellipsis if it exceeds max width.

        Args:
            text: Text to truncate
            font: PIL ImageFont
            max_width: Maximum width in pixels

        Returns:
            Truncated text (with ellipsis if needed)
        """
        # Create temporary draw object for measurement
        temp_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(temp_img)

        # Check if text fits
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            return text

        # Truncate with ellipsis
        ellipsis = "..."
        for i in range(len(text), 0, -1):
            truncated = text[:i] + ellipsis
            bbox = draw.textbbox((0, 0), truncated, font=font)
            text_width = bbox[2] - bbox[0]

            if text_width <= max_width:
                return truncated

        return ellipsis

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        """
        Wrap text into multiple lines to fit within max width.

        Args:
            text: Text to wrap
            font: PIL ImageFont
            max_width: Maximum width in pixels

        Returns:
            List of text lines
        """
        # Create temporary draw object for measurement
        temp_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(temp_img)

        words = text.split()
        lines = []
        current_line = []

        for word in words:
            # Try adding word to current line
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]

            if text_width <= max_width:
                current_line.append(word)
            else:
                # Start new line
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        # Add last line
        if current_line:
            lines.append(' '.join(current_line))

        return lines if lines else [text]
