"""
engine/ndvi.py

Computes NDVI (Normalized Difference Vegetation Index) for a given year
of Pune Sentinel-2 imagery.

Expects clipped, preprocessed inputs at:
    data/pune/pune_<year>clip.tif

(matching the naming convention already used in this project's data
directory; see scripts/clip_and_preprocess.py for how these are produced).

The input GeoTIFF is expected to contain at least two bands ordered as
[Red, NIR] (bands 1 and 2 respectively). If your source imagery uses a
different band order, adjust RED_BAND_INDEX / NIR_BAND_INDEX below.

Usage:
    python ndvi.py 2015
"""

import os
import sys
import numpy as np
import rasterio

from engine import raster_io

DATA_DIR = "data/pune"
RED_BAND_INDEX = 1  # 1-based rasterio band index for Red
NIR_BAND_INDEX = 2  # 1-based rasterio band index for NIR
VEGETATION_THRESHOLD = 0.3


def _load_red_nir(input_path):
    """
    Load the Red and NIR bands from a multi-band clipped GeoTIFF.

    Args:
        input_path (str): Path to the clipped GeoTIFF containing Red and
            NIR bands.

    Returns:
        tuple[np.ndarray, np.ndarray, dict]: (red, nir, profile)

    Raises:
        FileNotFoundError: If `input_path` does not exist.
        ValueError: If the raster does not contain enough bands.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input raster not found: {input_path}")

    try:
        with rasterio.open(input_path) as src:
            if src.count < max(RED_BAND_INDEX, NIR_BAND_INDEX):
                raise ValueError(
                    f"Expected at least {max(RED_BAND_INDEX, NIR_BAND_INDEX)} "
                    f"bands in '{input_path}', found {src.count}."
                )
            red = src.read(RED_BAND_INDEX).astype(np.float64)
            nir = src.read(NIR_BAND_INDEX).astype(np.float64)
            profile = src.profile.copy()
    except rasterio.errors.RasterioIOError as exc:
        raise ValueError(f"Could not open '{input_path}' as a raster: {exc}") from exc

    return red, nir, profile


def compute_ndvi(year: int) -> tuple[str, dict]:
    """
    Compute NDVI for a given year of Pune imagery.

    NDVI = (NIR - Red) / (NIR + Red), computed safely (divide-by-zero
    pixels are set to 0 rather than raising or producing NaN/inf).

    Args:
        year (int): Year of imagery to process, e.g. 2015. Input is
            expected at data/pune/pune_<year>clip.tif.

    Returns:
        tuple[str, dict]:
            - output_path: Path to the saved NDVI GeoTIFF
              (data/pune/ndvi<year>.tif).
            - stats: {
                  "mean_ndvi": float,
                  "vegetation_pixel_percent": float,
              }

    Raises:
        FileNotFoundError: If the expected input file for `year` is missing.
        ValueError: If the input raster is malformed.
    """
    input_path = os.path.join(DATA_DIR, f"pune_{year}clip.tif")
    output_path = os.path.join(DATA_DIR, f"ndvi{year}.tif")

    red, nir, profile = _load_red_nir(input_path)

    denominator = nir + red
    ndvi = np.zeros_like(denominator, dtype=np.float64)
    valid_mask = denominator != 0
    ndvi[valid_mask] = (nir[valid_mask] - red[valid_mask]) / denominator[valid_mask]
    ndvi = np.clip(ndvi, -1.0, 1.0)

    out_profile = profile.copy()
    out_profile.update(count=1, dtype="float64")
    raster_io.save_raster(ndvi, out_profile, output_path)

    mean_ndvi = float(np.mean(ndvi))
    vegetation_pixel_percent = float(
        np.sum(ndvi > VEGETATION_THRESHOLD) / ndvi.size * 100
    )

    stats = {
        "mean_ndvi": mean_ndvi,
        "vegetation_pixel_percent": vegetation_pixel_percent,
    }

    return output_path, stats


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ndvi.py <year>")
        sys.exit(1)

    try:
        year_arg = int(sys.argv[1])
    except ValueError:
        print("Error: <year> must be an integer, e.g. python ndvi.py 2015")
        sys.exit(1)

    try:
        path, result_stats = compute_ndvi(year_arg)
        print(f"NDVI raster saved to: {path}")
        print(f"Mean NDVI: {result_stats['mean_ndvi']:.4f}")
        print(
            f"Vegetation pixel percent (NDVI > {VEGETATION_THRESHOLD}): "
            f"{result_stats['vegetation_pixel_percent']:.2f}%"
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
