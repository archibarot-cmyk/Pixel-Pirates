"""
engine/change_detection.py

Detects vegetation change between two years by differencing their NDVI
rasters and classifying each pixel as loss, gain, or stable.

Usage:
    python change_detection.py 2015 2020
"""

import os
import sys
import numpy as np

from engine import raster_io
from engine.ndvi import compute_ndvi

DATA_DIR = "data/pune"

LOSS_THRESHOLD = -0.1
GAIN_THRESHOLD = 0.1

# Classification codes written into the output raster
LOSS_CODE = -1
STABLE_CODE = 0
GAIN_CODE = 1


def change_detection(year_1: int, year_2: int) -> tuple[str, dict]:
    """
    Compute NDVI-based change detection between two years.

    Runs compute_ndvi() for both years, subtracts them (year_2 - year_1),
    and classifies each pixel as:
        - loss:   difference < -0.1
        - gain:   difference > 0.1
        - stable: otherwise

    Args:
        year_1 (int): Baseline year (e.g. 2015).
        year_2 (int): Comparison year (e.g. 2020).

    Returns:
        tuple[str, dict]:
            - output_path: Path to the saved classified change raster
              (data/pune/change_<year_1>_<year_2>.tif). Pixel values are
              -1 (loss), 0 (stable), 1 (gain).
            - stats: {
                  "area_lost_sq_km": float,
                  "area_gained_sq_km": float,
                  "percent_change": float,
              }

    Raises:
        FileNotFoundError: If input imagery for either year is missing.
        ValueError: If the NDVI rasters are malformed or pixel size is
            unavailable to compute area.
    """
    ndvi1_path, _ = compute_ndvi(year_1)
    ndvi2_path, _ = compute_ndvi(year_2)

    ndvi1, profile1 = raster_io.load_band(ndvi1_path)
    ndvi2, profile2 = raster_io.load_band(ndvi2_path)

    if ndvi1.shape != ndvi2.shape:
        raise ValueError(
            f"NDVI rasters for {year_1} and {year_2} have different shapes "
            f"({ndvi1.shape} vs {ndvi2.shape}); align them before comparing."
        )

    difference = ndvi2 - ndvi1

    classification = np.full(difference.shape, STABLE_CODE, dtype=np.int16)
    classification[difference < LOSS_THRESHOLD] = LOSS_CODE
    classification[difference > GAIN_THRESHOLD] = GAIN_CODE

    output_path = os.path.join(DATA_DIR, f"change_{year_1}_{year_2}.tif")
    out_profile = profile1.copy()
    out_profile.update(count=1, dtype="int16")
    raster_io.save_raster(classification.astype(np.int16), out_profile, output_path)

    # Determine pixel area (sq km) from the transform's pixel resolution.
    transform = profile1.get("transform")
    if transform is None:
        raise ValueError("Source NDVI raster is missing a geotransform; cannot compute area.")

    pixel_width = abs(transform.a)
    pixel_height = abs(transform.e)
    pixel_area_sq_m = pixel_width * pixel_height
    pixel_area_sq_km = pixel_area_sq_m / 1_000_000

    loss_pixel_count = int(np.sum(classification == LOSS_CODE))
    gain_pixel_count = int(np.sum(classification == GAIN_CODE))
    total_pixel_count = classification.size

    area_lost_sq_km = loss_pixel_count * pixel_area_sq_km
    area_gained_sq_km = gain_pixel_count * pixel_area_sq_km
    percent_change = float((gain_pixel_count - loss_pixel_count) / total_pixel_count * 100)

    stats = {
        "area_lost_sq_km": float(area_lost_sq_km),
        "area_gained_sq_km": float(area_gained_sq_km),
        "percent_change": percent_change,
    }

    return output_path, stats


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python change_detection.py <year_1> <year_2>")
        sys.exit(1)

    try:
        y1 = int(sys.argv[1])
        y2 = int(sys.argv[2])
    except ValueError:
        print("Error: years must be integers, e.g. python change_detection.py 2015 2020")
        sys.exit(1)

    try:
        path, result_stats = change_detection(y1, y2)
        print(f"Change raster saved to: {path}")
        print(f"Area lost: {result_stats['area_lost_sq_km']:.4f} sq km")
        print(f"Area gained: {result_stats['area_gained_sq_km']:.4f} sq km")
        print(f"Percent change: {result_stats['percent_change']:.2f}%")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
