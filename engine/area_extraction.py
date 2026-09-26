"""
engine/area_extraction.py

Extracts a binary vegetation mask from NDVI for a given year and
computes the total vegetated area.

Usage:
    python area_extraction.py 2015
    python area_extraction.py 2015 --threshold 0.4
"""

import os
import sys
import argparse
import numpy as np

from engine import raster_io
from engine.ndvi import compute_ndvi

DATA_DIR = "data/pune"
DEFAULT_THRESHOLD = 0.3

VEGETATION_CODE = 1
NON_VEGETATION_CODE = 0


def area_extraction(year: int, threshold: float = DEFAULT_THRESHOLD) -> tuple[str, dict]:
    """
    Extract a binary vegetation mask from NDVI for a given year.

    Args:
        year (int): Year of imagery to process (e.g. 2015).
        threshold (float): NDVI threshold above which a pixel is
            classified as vegetation. Defaults to 0.3.

    Returns:
        tuple[str, dict]:
            - output_path: Path to the saved binary mask GeoTIFF
              (data/pune/vegetation_mask_<year>.tif). Pixel values are
              1 (vegetation) or 0 (non-vegetation).
            - stats: {
                  "total_vegetation_area_sq_km": float,
                  "percent_of_total_area": float,
              }

    Raises:
        FileNotFoundError: If input imagery for `year` is missing.
        ValueError: If the NDVI raster is malformed or pixel size is
            unavailable to compute area.
    """
    ndvi_path, _ = compute_ndvi(year)
    ndvi, profile = raster_io.load_band(ndvi_path)

    mask = np.where(ndvi > threshold, VEGETATION_CODE, NON_VEGETATION_CODE).astype(np.int16)

    output_path = os.path.join(DATA_DIR, f"vegetation_mask_{year}.tif")
    out_profile = profile.copy()
    out_profile.update(count=1, dtype="int16")
    raster_io.save_raster(mask, out_profile, output_path)

    transform = profile.get("transform")
    if transform is None:
        raise ValueError("NDVI raster is missing a geotransform; cannot compute area.")

    pixel_width = abs(transform.a)
    pixel_height = abs(transform.e)
    pixel_area_sq_km = (pixel_width * pixel_height) / 1_000_000

    vegetation_pixel_count = int(np.sum(mask == VEGETATION_CODE))
    total_pixel_count = mask.size

    total_vegetation_area_sq_km = vegetation_pixel_count * pixel_area_sq_km
    percent_of_total_area = float(vegetation_pixel_count / total_pixel_count * 100)

    stats = {
        "total_vegetation_area_sq_km": float(total_vegetation_area_sq_km),
        "percent_of_total_area": percent_of_total_area,
    }

    return output_path, stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract vegetation area from NDVI.")
    parser.add_argument("year", type=int, help="Year of imagery to process, e.g. 2015")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"NDVI threshold for vegetation classification (default: {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    try:
        path, result_stats = area_extraction(args.year, args.threshold)
        print(f"Vegetation mask saved to: {path}")
        print(
            f"Total vegetation area: "
            f"{result_stats['total_vegetation_area_sq_km']:.4f} sq km"
        )
        print(f"Percent of total area: {result_stats['percent_of_total_area']:.2f}%")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
