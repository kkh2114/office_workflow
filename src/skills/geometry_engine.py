"""
Geometry Engine Skill
Provides geometric calculations and operations for architectural design.
"""

import math
from typing import List, Tuple, Optional
from shapely.geometry import Polygon as ShapelyPolygon, Point
from shapely.ops import unary_union


class GeometryEngine:
    """Geometric calculations for architectural elements."""

    @staticmethod
    def calculate_polygon_area(coordinates: List[List[float]]) -> float:
        """
        Calculate the area of a polygon.

        Args:
            coordinates: List of [x, y] coordinate pairs

        Returns:
            Area in square meters
        """
        poly = ShapelyPolygon(coordinates)
        return poly.area

    @staticmethod
    def calculate_polygon_perimeter(coordinates: List[List[float]]) -> float:
        """
        Calculate the perimeter of a polygon.

        Args:
            coordinates: List of [x, y] coordinate pairs

        Returns:
            Perimeter in meters
        """
        poly = ShapelyPolygon(coordinates)
        return poly.length

    @staticmethod
    def calculate_centroid(coordinates: List[List[float]]) -> Tuple[float, float]:
        """
        Calculate the centroid of a polygon.

        Args:
            coordinates: List of [x, y] coordinate pairs

        Returns:
            (x, y) centroid coordinates
        """
        poly = ShapelyPolygon(coordinates)
        centroid = poly.centroid
        return (centroid.x, centroid.y)

    @staticmethod
    def is_point_inside_polygon(
        point: Tuple[float, float],
        coordinates: List[List[float]]
    ) -> bool:
        """
        Check if a point is inside a polygon.

        Args:
            point: (x, y) point coordinates
            coordinates: List of [x, y] coordinate pairs forming polygon

        Returns:
            True if point is inside polygon
        """
        poly = ShapelyPolygon(coordinates)
        pt = Point(point)
        return poly.contains(pt)

    @staticmethod
    def calculate_wall_length(
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> float:
        """
        Calculate the length of a wall.

        Args:
            start: (x, y) start point
            end: (x, y) end point

        Returns:
            Length in meters
        """
        return math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)

    @staticmethod
    def calculate_wall_angle(
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> float:
        """
        Calculate the angle of a wall relative to X-axis.

        Args:
            start: (x, y) start point
            end: (x, y) end point

        Returns:
            Angle in degrees
        """
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        return math.degrees(math.atan2(dy, dx))

    @staticmethod
    def offset_line(
        start: Tuple[float, float],
        end: Tuple[float, float],
        distance: float
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Offset a line perpendicular to its direction.

        Args:
            start: (x, y) start point
            end: (x, y) end point
            distance: Offset distance (positive = left, negative = right)

        Returns:
            Tuple of new (start, end) points
        """
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx**2 + dy**2)

        if length == 0:
            return (start, end)

        # Unit perpendicular vector
        perp_x = -dy / length * distance
        perp_y = dx / length * distance

        new_start = (start[0] + perp_x, start[1] + perp_y)
        new_end = (end[0] + perp_x, end[1] + perp_y)

        return (new_start, new_end)

    @staticmethod
    def calculate_bounding_box(
        coordinates: List[List[float]]
    ) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box of a polygon.

        Args:
            coordinates: List of [x, y] coordinate pairs

        Returns:
            (min_x, min_y, max_x, max_y)
        """
        poly = ShapelyPolygon(coordinates)
        return poly.bounds

    @staticmethod
    def simplify_polygon(
        coordinates: List[List[float]],
        tolerance: float = 0.01
    ) -> List[List[float]]:
        """
        Simplify a polygon by removing nearly collinear points.

        Args:
            coordinates: List of [x, y] coordinate pairs
            tolerance: Simplification tolerance in meters

        Returns:
            Simplified coordinate list
        """
        poly = ShapelyPolygon(coordinates)
        simplified = poly.simplify(tolerance, preserve_topology=True)
        return list(simplified.exterior.coords)

    @staticmethod
    def check_polygon_overlap(
        coords1: List[List[float]],
        coords2: List[List[float]]
    ) -> bool:
        """
        Check if two polygons overlap.

        Args:
            coords1: First polygon coordinates
            coords2: Second polygon coordinates

        Returns:
            True if polygons overlap
        """
        poly1 = ShapelyPolygon(coords1)
        poly2 = ShapelyPolygon(coords2)
        return poly1.intersects(poly2)

    @staticmethod
    def calculate_intersection_area(
        coords1: List[List[float]],
        coords2: List[List[float]]
    ) -> float:
        """
        Calculate the intersection area of two polygons.

        Args:
            coords1: First polygon coordinates
            coords2: Second polygon coordinates

        Returns:
            Intersection area in square meters
        """
        poly1 = ShapelyPolygon(coords1)
        poly2 = ShapelyPolygon(coords2)
        intersection = poly1.intersection(poly2)
        return intersection.area

    @staticmethod
    def rotate_point(
        point: Tuple[float, float],
        center: Tuple[float, float],
        angle_degrees: float
    ) -> Tuple[float, float]:
        """
        Rotate a point around a center.

        Args:
            point: (x, y) point to rotate
            center: (x, y) rotation center
            angle_degrees: Rotation angle in degrees

        Returns:
            Rotated (x, y) coordinates
        """
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Translate to origin
        dx = point[0] - center[0]
        dy = point[1] - center[1]

        # Rotate
        new_x = dx * cos_a - dy * sin_a
        new_y = dx * sin_a + dy * cos_a

        # Translate back
        return (new_x + center[0], new_y + center[1])

    @staticmethod
    def calculate_door_opening_points(
        wall_start: Tuple[float, float],
        wall_end: Tuple[float, float],
        position: float,
        width: float
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Calculate door opening points on a wall.

        Args:
            wall_start: Wall start point
            wall_end: Wall end point
            position: Position along wall (0.0-1.0)
            width: Door width

        Returns:
            (opening_start, opening_end) points
        """
        dx = wall_end[0] - wall_start[0]
        dy = wall_end[1] - wall_start[1]
        wall_length = math.sqrt(dx**2 + dy**2)

        if wall_length == 0:
            return (wall_start, wall_end)

        unit_dx = dx / wall_length
        unit_dy = dy / wall_length

        # Door center point
        center_x = wall_start[0] + dx * position
        center_y = wall_start[1] + dy * position

        # Opening points
        half_width = width / 2
        opening_start = (
            center_x - unit_dx * half_width,
            center_y - unit_dy * half_width
        )
        opening_end = (
            center_x + unit_dx * half_width,
            center_y + unit_dy * half_width
        )

        return (opening_start, opening_end)
