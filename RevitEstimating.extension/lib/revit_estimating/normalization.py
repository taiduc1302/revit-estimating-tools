# -*- coding: utf-8 -*-
"""Revit internal-unit normalization helpers.

Revit stores common model lengths in feet. These conversions are intentionally
simple and deterministic so the same raw values produce the same exports.
"""
from __future__ import absolute_import, division, print_function

from .utils import rounded

FEET_TO_METERS = 0.3048
FEET_TO_MILLIMETERS = 304.8
SQFT_TO_SQM = 0.09290304
CUFT_TO_CUM = 0.028316846592


def length_ft_to_m(value):
    return None if value is None else rounded(float(value) * FEET_TO_METERS)


def length_ft_to_mm(value):
    return None if value is None else rounded(float(value) * FEET_TO_MILLIMETERS, 3)


def area_sqft_to_sqm(value):
    return None if value is None else rounded(float(value) * SQFT_TO_SQM)


def volume_cuft_to_cum(value):
    return None if value is None else rounded(float(value) * CUFT_TO_CUM)


def normalize_quantity(quantity_type, raw_value):
    if raw_value is None:
        return None, None
    quantity_type = (quantity_type or "").upper()
    if quantity_type == "LENGTH":
        return length_ft_to_m(raw_value), "M"
    if quantity_type == "AREA":
        return area_sqft_to_sqm(raw_value), "M2"
    if quantity_type == "VOLUME":
        return volume_cuft_to_cum(raw_value), "M3"
    if quantity_type == "COUNT":
        return rounded(raw_value, 0), "EA"
    return None, None
