"""What a page holds, as far as encoding cares: how much of it images cover, and so whether lossy WebP suits it."""

from .image_coverage import IMAGE_COVERAGE_KEY, PHOTO_HEAVY_COVERAGE, measure_image_coverage, suits_lossy_encoding

__all__ = ["IMAGE_COVERAGE_KEY", "PHOTO_HEAVY_COVERAGE", "measure_image_coverage", "suits_lossy_encoding"]
