"""
scripts/clip_and_preprocess.py

Clips a raw Sentinel-2 GeoTIFF to a bounding box (e.g. for Pune) and saves
the result as a preprocessed input for the engine pipeline.

Usage:
    python scripts/clip_and_preprocess.py \\
        --input /path/to/raw_sentinel2.tif \\
        --bbox 73.74 18.44 73.98 18.62 \\
        --output data/pune/pune_2015_clip.tif \\
        --year 2015

The bounding box is given as: min_lon min_lat max_lon max_lat
(in the same CRS as the input raster, typically EPSG:4326 or the
raster's native UTM zone).
"""

import os
import sys
import argparse

import rasterio
from rasterio.windows import from_bounds
from rasterio.errors import RasterioIOError


def clip_raster(input_path, bbox, output_path, year):
    """
    Clip a raster to a bounding box and save it.

    Args:
        input_path (str): Path to the raw input GeoTIFF.
        bbox (tuple[float, float, float, float]): (min_lon, min_lat,
            max_lon, max_lat) in the raster's CRS.
        output_path (str): Where to save the clipped GeoTIFF.
        year (int): Year label, used only for logging/output naming
            consistency with the rest of the pipeline.

    Raises:
        FileNotFoundError: If `input_path` does not exist.
        ValueError: If the bounding box does not intersect the raster,
            or the raster cannot be opened.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input raster not found: {input_path}")

    min_lon, min_lat, max_lon, max_lat = bbox

    try:
        with rasterio.open(input_path) as src:
            window = from_bounds(min_lon, min_lat, max_lon, max_lat, transform=src.transform)

            window_width = window.width
            window_height = window.height
            if window_width <= 0 or window_height <= 0:
                raise ValueError(
                    f"Bounding box {bbox} does not intersect raster '{input_path}'."
                )

            clipped_transform = src.window_transform(window)
            data = src.read(window=window)

            out_profile = src.profile.copy()
            out_profile.update(
                {
                    "height": data.shape[1],
                    "width": data.shape[2],
                    "transform": clipped_transform,
                }
            )

            out_dir = os.path.dirname(output_path)
            if out_dir and not os.path.isdir(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            with rasterio.open(output_path, "w", **out_profile) as dst:
                dst.write(data)

    except RasterioIOError as exc:
        raise ValueError(f"Could not open '{input_path}' as a raster: {exc}") from exc

    print(f"Clipped raster for year {year} saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Clip a raw Sentinel-2 GeoTIFF to a bounding box (e.g. Pune)."
    )
    parser.add_argument("--input", required=True, help="Path to the raw Sentinel-2 GeoTIFF.")
    parser.add_argument(
        "--bbox",
        required=True,
        nargs=4,
        type=float,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Bounding box: min_lon min_lat max_lon max_lat",
    )
    parser.add_argument("--output", required=True, help="Path to save the clipped GeoTIFF.")
    parser.add_argument("--year", required=True, type=int, help="Year of the imagery, e.g. 2015")

    args = parser.parse_args()

    try:
        clip_raster(args.input, tuple(args.bbox), args.output, args.year)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
