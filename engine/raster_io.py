"""
engine/raster_io.py

Shared raster I/O utilities built on top of rasterio and numpy.

Provides:
    load_band(path)                    -> (array, profile)
    save_raster(array, profile, path)  -> None
    reproject_and_align(src_path, ref_path) -> (array, profile)

These helpers are intentionally generic so that engine/ndvi.py,
engine/change_detection.py, and engine/area_extraction.py can share
one consistent, well-tested way of reading and writing GeoTIFFs.
"""

import os
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject


def load_band(path):
    """
    Read a single-band GeoTIFF and return its data and metadata.

    Args:
        path (str): Path to a single-band GeoTIFF file.

    Returns:
        tuple[np.ndarray, dict]:
            - 2D numpy array of the raster's first band, as float64.
            - The rasterio profile (metadata) describing the file,
              which can be reused directly with save_raster().

    Raises:
        FileNotFoundError: If `path` does not exist.
        ValueError: If the file exists but cannot be opened as a raster,
            or if it contains no bands.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Raster file not found: {path}")

    try:
        with rasterio.open(path) as src:
            if src.count < 1:
                raise ValueError(f"Raster at {path} has no bands to read.")
            array = src.read(1).astype(np.float64)
            profile = src.profile.copy()
    except rasterio.errors.RasterioIOError as exc:
        raise ValueError(f"Could not open '{path}' as a raster: {exc}") from exc

    return array, profile


def save_raster(array, profile, output_path):
    """
    Write a numpy array to a new GeoTIFF using a given rasterio profile.

    Args:
        array (np.ndarray): 2D array to write as a single band.
        profile (dict): A rasterio profile (e.g. from load_band()) describing
            CRS, transform, width, height, etc. The dtype and band count
            are adjusted automatically to match `array`.
        output_path (str): Destination path for the new GeoTIFF. Parent
            directories are created if they do not already exist.

    Raises:
        ValueError: If `array` is not a 2D array or `profile` is missing.
    """
    if array is None or array.ndim != 2:
        raise ValueError("save_raster expects a 2D numpy array.")
    if not profile:
        raise ValueError("save_raster requires a valid rasterio profile.")

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    out_profile = profile.copy()
    out_profile.update(
        {
            "count": 1,
            "dtype": array.dtype,
            "height": array.shape[0],
            "width": array.shape[1],
        }
    )

    try:
        with rasterio.open(output_path, "w", **out_profile) as dst:
            dst.write(array, 1)
    except rasterio.errors.RasterioIOError as exc:
        raise ValueError(f"Could not write raster to '{output_path}': {exc}") from exc


def reproject_and_align(src_path, ref_path):
    """
    Reproject/resample a source raster onto the same CRS, resolution, and
    extent (grid) as a reference raster, if they don't already match.

    If the source raster's CRS, transform, and shape already match the
    reference raster, the source data is returned unchanged (no
    reprojection is performed).

    Args:
        src_path (str): Path to the raster that should be aligned.
        ref_path (str): Path to the reference raster whose grid/CRS the
            source should be matched to.

    Returns:
        tuple[np.ndarray, dict]:
            - 2D numpy array of the (possibly reprojected) source band,
              aligned to the reference grid.
            - The rasterio profile describing the aligned array (matches
              the reference raster's CRS/transform/shape).

    Raises:
        FileNotFoundError: If either `src_path` or `ref_path` does not exist.
        ValueError: If either file cannot be opened as a raster.
    """
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"Source raster not found: {src_path}")
    if not os.path.isfile(ref_path):
        raise FileNotFoundError(f"Reference raster not found: {ref_path}")

    try:
        with rasterio.open(src_path) as src, rasterio.open(ref_path) as ref:
            same_crs = src.crs == ref.crs
            same_transform = src.transform == ref.transform
            same_shape = (src.width, src.height) == (ref.width, ref.height)

            if same_crs and same_transform and same_shape:
                array = src.read(1).astype(np.float64)
                profile = src.profile.copy()
                return array, profile

            dst_transform, dst_width, dst_height = calculate_default_transform(
                src.crs,
                ref.crs,
                ref.width,
                ref.height,
                *ref.bounds,
            )
            # Align exactly onto the reference grid (same transform/shape).
            dst_transform = ref.transform
            dst_width = ref.width
            dst_height = ref.height

            dst_array = np.zeros((dst_height, dst_width), dtype=np.float64)

            reproject(
                source=rasterio.band(src, 1),
                destination=dst_array,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=ref.crs,
                resampling=Resampling.bilinear,
            )

            out_profile = src.profile.copy()
            out_profile.update(
                {
                    "crs": ref.crs,
                    "transform": dst_transform,
                    "width": dst_width,
                    "height": dst_height,
                    "dtype": "float64",
                }
            )

            return dst_array, out_profile
    except rasterio.errors.RasterioIOError as exc:
        raise ValueError(
            f"Could not open '{src_path}' or '{ref_path}' as rasters: {exc}"
        ) from exc
