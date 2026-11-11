"""
Bounding Box utilities for coordinate normalization.

This module provides classes for calculating and working with bounding boxes
that enclose LED devices in a unified world space.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class GlobalBoundingBox:
    """
    Bounding box that encloses all active devices in a unified world space.
    Used for normalizing LED coordinates to [0,1] range.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def width(self) -> float:
        """Calculate bbox width."""
        return self.max_x - self.min_x

    def height(self) -> float:
        """Calculate bbox height."""
        return self.max_y - self.min_y

    def normalize_point(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Normalize a world coordinate to [0,1] space.

        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space

        Returns:
            (norm_x, norm_y) where 0.0 <= norm_x, norm_y <= 1.0
        """
        width = self.width()
        height = self.height()

        norm_x = (world_x - self.min_x) / width if width > 0 else 0.5
        norm_y = (world_y - self.min_y) / height if height > 0 else 0.5

        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)
