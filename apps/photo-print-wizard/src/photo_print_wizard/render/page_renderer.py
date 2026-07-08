"""Renders a Page onto any Cairo context (screen preview, PDF surface, or
raster ImageSurface) using a single px-per-mm scale factor, so the exact
same code path guarantees preview == print.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

import cairo
from PIL import Image

from ..imaging.crop import apply_crop
from ..imaging.loader import load_image
from ..layout.geometry import Border, Page, PageImage
from ..layout.units import mm_to_pt, mm_to_px

# Signature: (PageImage, target_px:(w,h)) -> PIL.Image sized exactly target_px
ImageResolver = Callable[[PageImage, tuple[int, int]], Image.Image]


def default_image_resolver(page_image: PageImage, target_px: tuple[int, int]) -> Image.Image:
    img = load_image(page_image.source_path)
    if page_image.rotation_deg:
        img = img.rotate(-page_image.rotation_deg, expand=True)
    return apply_crop(img, target_px, mode=page_image.crop_mode, alignment=page_image.alignment)


def _pil_to_cairo_surface(img: Image.Image) -> cairo.ImageSurface:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    buf.seek(0)
    return cairo.ImageSurface.create_from_png(buf)


def render_page(
    cr: cairo.Context,
    page: Page,
    px_per_mm: float,
    background_rgb: tuple[float, float, float] = (1.0, 1.0, 1.0),
    border: Border | None = None,
    show_guides: bool = False,
    image_resolver: ImageResolver = default_image_resolver,
    image_dpi: float | None = None,
) -> None:
    """Draws `page` into `cr`. Caller is responsible for the context's
    coordinate system origin (0,0 = page top-left) and clip.

    `image_dpi` controls the pixel resolution images are rasterized at,
    independent of `px_per_mm` (which is the *geometry* scale — e.g. ~2.83
    px/mm for a PDF's point-based coordinate space). Without this
    decoupling, PDF export would rasterize photos at ~72 DPI just because
    PDF points are a low-density unit. Pass a real print DPI (300 is the
    default for export) to keep source-image quality in the output; leave
    as None to derive DPI from px_per_mm (correct for on-screen preview,
    where rendering at screen density is desired and cheap).
    """
    page_w = page.paper.width_mm * px_per_mm
    page_h = page.paper.height_mm * px_per_mm

    cr.save()
    cr.set_source_rgb(*background_rgb)
    cr.rectangle(0, 0, page_w, page_h)
    cr.fill()
    cr.restore()

    for slot, page_image in page.placements:
        x = slot.x_mm * px_per_mm
        y = slot.y_mm * px_per_mm
        w = slot.width_mm * px_per_mm
        h = slot.height_mm * px_per_mm

        if page_image is not None:
            raster_dpi = image_dpi if image_dpi is not None else px_per_mm * 25.4
            target_px = (
                max(1, round(mm_to_px(slot.width_mm, raster_dpi))),
                max(1, round(mm_to_px(slot.height_mm, raster_dpi))),
            )
            pil_img = image_resolver(page_image, target_px)
            surface = _pil_to_cairo_surface(pil_img)
            sw, sh = target_px

            cr.save()
            if border and border.rounded_radius_mm > 0:
                _rounded_rect_path(cr, x, y, w, h, border.rounded_radius_mm * px_per_mm)
                cr.clip()
            cr.translate(x, y)
            cr.scale(w / sw, h / sh)
            cr.set_source_surface(surface, 0, 0)
            cr.paint()
            cr.restore()

            if border and border.width_mm > 0:
                cr.save()
                cr.set_source_rgb(*border.color_rgb)
                cr.set_line_width(border.width_mm * px_per_mm)
                if border.rounded_radius_mm > 0:
                    _rounded_rect_path(cr, x, y, w, h, border.rounded_radius_mm * px_per_mm)
                else:
                    cr.rectangle(x, y, w, h)
                cr.stroke()
                cr.restore()
        elif show_guides:
            cr.save()
            cr.set_source_rgba(0.6, 0.6, 0.6, 0.4)
            cr.set_dash([4, 4])
            cr.set_line_width(1)
            cr.rectangle(x, y, w, h)
            cr.stroke()
            cr.restore()

    if show_guides:
        _draw_margin_guides(cr, page, px_per_mm)


def _rounded_rect_path(cr: cairo.Context, x, y, w, h, r) -> None:
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.5708, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
    cr.arc(x + r, y + r, r, 3.1416, 4.7124)
    cr.close_path()


def _draw_margin_guides(cr: cairo.Context, page: Page, px_per_mm: float) -> None:
    cr.save()
    cr.set_source_rgba(0.2, 0.4, 1.0, 0.5)
    cr.set_dash([2, 3])
    cr.set_line_width(1)
    cr.rectangle(0, 0, page.paper.width_mm * px_per_mm, page.paper.height_mm * px_per_mm)
    cr.stroke()
    cr.restore()


def export_pdf(
    pages: list[Page],
    output_path: str | Path,
    background_rgb: tuple[float, float, float] = (1.0, 1.0, 1.0),
    border: Border | None = None,
    image_resolver: ImageResolver = default_image_resolver,
    image_dpi: float = 300.0,
) -> None:
    """Vector PDF at true physical size (1 mm = mm_to_pt(1) pt). Photos are
    rasterized at `image_dpi` (default 300, real print quality) regardless
    of the PDF's low-density point-based coordinate space."""
    if not pages:
        raise ValueError("No pages to export.")

    px_per_mm = mm_to_pt(1.0)  # cairo PDF surface user units are points
    first = pages[0]
    surface = cairo.PDFSurface(
        str(output_path),
        first.paper.width_mm * px_per_mm,
        first.paper.height_mm * px_per_mm,
    )
    cr = cairo.Context(surface)

    for page in pages:
        surface.set_size(page.paper.width_mm * px_per_mm, page.paper.height_mm * px_per_mm)
        render_page(
            cr,
            page,
            px_per_mm,
            background_rgb,
            border,
            image_resolver=image_resolver,
            image_dpi=image_dpi,
        )
        surface.show_page()

    surface.finish()


def export_raster(
    page: Page,
    output_path: str | Path,
    dpi: float = 300.0,
    background_rgb: tuple[float, float, float] = (1.0, 1.0, 1.0),
    border: Border | None = None,
    image_resolver: ImageResolver = default_image_resolver,
    fmt: str | None = None,
) -> None:
    """Renders a single page to PNG/JPEG/TIFF at `dpi`."""
    px_per_mm = dpi / 25.4
    w = round(mm_to_px(page.paper.width_mm, dpi))
    h = round(mm_to_px(page.paper.height_mm, dpi))

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surface)
    render_page(
        cr, page, px_per_mm, background_rgb, border, image_resolver=image_resolver, image_dpi=dpi
    )

    buf = io.BytesIO()
    surface.write_to_png(buf)
    buf.seek(0)
    img = Image.open(buf).convert("RGB")

    output_path = Path(output_path)
    save_fmt = fmt or output_path.suffix.lstrip(".").upper().replace("JPG", "JPEG")
    img.save(output_path, save_fmt, dpi=(dpi, dpi))
