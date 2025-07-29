"""Sewpat package - A Python library for 2D CAD operations.

This package provides geometric primitives for CAD operations,
designed for generating and manipulating vector patterns.

Modules:
    geometry: Contains geometric primitives like Point, Line, Ray, and Circle.
"""

from .geometry import Point, Segment, Ray, Circle, Line
from .part import PatternPart

__all__ = ['Point', 'Segment', 'Ray', 'Circle', 'Line', 'PatternPart']
