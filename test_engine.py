"""
tests/test_engine.py

Integration tests for the engine package (NDVI, change detection, and
area extraction) against real raster data in data/pune/ for 2015 and 2020.

Run with:
    pytest tests/test_engine.py -v
"""

import os
import pytest

from engine.ndvi import compute_ndvi
from engine.change_detection import change_detection
from engine.area_extraction import area_extraction

YEAR_1 = 2015
YEAR_2 = 2020

REQUIRED_INPUTS = [
    os.path.join("data", "pune", f"pune_{YEAR_1}clip.tif"),
    os.path.join("data", "pune", f"pune_{YEAR_2}clip.tif"),
]

missing_inputs = [p for p in REQUIRED_INPUTS if not os.path.isfile(p)]

pytestmark = pytest.mark.skipif(
    bool(missing_inputs),
    reason=f"Missing required input raster(s): {missing_inputs}",
)


@pytest.mark.parametrize("year", [YEAR_1, YEAR_2])
def test_compute_ndvi(year):
    """compute_ndvi should return a real file and sane NDVI stats."""
    output_path, stats = compute_ndvi(year)

    assert os.path.isfile(output_path), f"NDVI output file missing: {output_path}"

    assert "mean_ndvi" in stats
    assert "vegetation_pixel_percent" in stats

    assert -1.0 <= stats["mean_ndvi"] <= 1.0
    assert 0.0 <= stats["vegetation_pixel_percent"] <= 100.0


def test_change_detection():
    """change_detection should return a real file and sane change stats."""
    output_path, stats = change_detection(YEAR_1, YEAR_2)

    assert os.path.isfile(output_path), f"Change detection output file missing: {output_path}"

    assert "area_lost_sq_km" in stats
    assert "area_gained_sq_km" in stats
    assert "percent_change" in stats

    assert stats["area_lost_sq_km"] >= 0.0
    assert stats["area_gained_sq_km"] >= 0.0
    assert -100.0 <= stats["percent_change"] <= 100.0


@pytest.mark.parametrize("year", [YEAR_1, YEAR_2])
def test_area_extraction(year):
    """area_extraction should return a real file and sane area stats."""
    output_path, stats = area_extraction(year)

    assert os.path.isfile(output_path), f"Area extraction output file missing: {output_path}"

    assert "total_vegetation_area_sq_km" in stats
    assert "percent_of_total_area" in stats

    assert stats["total_vegetation_area_sq_km"] >= 0.0
    assert 0.0 <= stats["percent_of_total_area"] <= 100.0
