"""
DXF Generator Skill
Generates AutoCAD DXF files from architectural design specifications using ezdxf library.
"""

import math
from pathlib import Path
from typing import List, Tuple, Optional
import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.gfxattribs import GfxAttribs

from ..models.design_spec import DesignSpec, Room, Door, Window, Furniture


class DXFGenerator:
    """
    Generates DXF files from design specifications.
    Uses ezdxf library (no AutoCAD installation required).
    """

    def __init__(self, wall_thickness: float = 0.2):
        """
        Initialize DXF Generator.

        Args:
            wall_thickness: Default wall thickness in meters
        """
        self.wall_thickness = wall_thickness
        self.doc = None
        self.msp = None

    def create_new_document(self, version: str = "R2018") -> None:
        """Create a new DXF document."""
        self.doc = ezdxf.new(version)
        self.msp = self.doc.modelspace()
        self._setup_layers()

    def _setup_layers(self) -> None:
        """Set up standard CAD layers."""
        layers = {
            "WALL": {"color": 7, "linetype": "CONTINUOUS"},  # White/Black
            "DOOR": {"color": 3, "linetype": "CONTINUOUS"},  # Green
            "WINDOW": {"color": 4, "linetype": "CONTINUOUS"},  # Cyan
            "FURNITURE": {"color": 8, "linetype": "CONTINUOUS"},  # Gray
            "DIMENSION": {"color": 1, "linetype": "CONTINUOUS"},  # Red
            "TEXT": {"color": 2, "linetype": "CONTINUOUS"},  # Yellow
            "CENTERLINE": {"color": 5, "linetype": "CENTER"},  # Blue
        }

        for name, props in layers.items():
            self.doc.layers.add(
                name=name,
                color=props["color"],
                linetype=props["linetype"]
            )

    def create_wall(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        thickness: Optional[float] = None
    ) -> None:
        """
        Create a wall as double lines.

        Args:
            start: (x, y) start point
            end: (x, y) end point
            thickness: Wall thickness (uses default if None)
        """
        if thickness is None:
            thickness = self.wall_thickness

        # Calculate perpendicular offset
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx**2 + dy**2)

        if length == 0:
            return

        # Unit perpendicular vector
        perp_x = -dy / length * (thickness / 2)
        perp_y = dx / length * (thickness / 2)

        # Outer wall lines
        outer1_start = (start[0] + perp_x, start[1] + perp_y)
        outer1_end = (end[0] + perp_x, end[1] + perp_y)

        outer2_start = (start[0] - perp_x, start[1] - perp_y)
        outer2_end = (end[0] - perp_x, end[1] - perp_y)

        # Draw wall lines
        self.msp.add_line(outer1_start, outer1_end, dxfattribs={"layer": "WALL"})
        self.msp.add_line(outer2_start, outer2_end, dxfattribs={"layer": "WALL"})

        # Draw end caps
        self.msp.add_line(outer1_start, outer2_start, dxfattribs={"layer": "WALL"})
        self.msp.add_line(outer1_end, outer2_end, dxfattribs={"layer": "WALL"})

    def create_door(
        self,
        wall_start: Tuple[float, float],
        wall_end: Tuple[float, float],
        door: Door
    ) -> None:
        """
        Create a door opening and swing arc.

        Args:
            wall_start: Wall start point
            wall_end: Wall end point
            door: Door specification
        """
        # Calculate door position along the wall
        dx = wall_end[0] - wall_start[0]
        dy = wall_end[1] - wall_start[1]

        door_center_x = wall_start[0] + dx * door.position
        door_center_y = wall_start[1] + dy * door.position

        # Calculate door opening points
        wall_length = math.sqrt(dx**2 + dy**2)
        unit_dx = dx / wall_length
        unit_dy = dy / wall_length

        half_width = door.width / 2
        opening_start = (
            door_center_x - unit_dx * half_width,
            door_center_y - unit_dy * half_width
        )
        opening_end = (
            door_center_x + unit_dx * half_width,
            door_center_y + unit_dy * half_width
        )

        # Draw door opening (line)
        self.msp.add_line(opening_start, opening_end, dxfattribs={"layer": "DOOR"})

        # Draw door swing arc
        wall_angle = math.degrees(math.atan2(dy, dx))

        if door.swing_direction == "inward":
            swing_angle = wall_angle + 90
        else:
            swing_angle = wall_angle - 90

        # Door arc (90 degrees)
        self.msp.add_arc(
            center=opening_start,
            radius=door.width,
            start_angle=swing_angle,
            end_angle=swing_angle + 90,
            dxfattribs={"layer": "DOOR"}
        )

    def create_window(
        self,
        wall_start: Tuple[float, float],
        wall_end: Tuple[float, float],
        window: Window
    ) -> None:
        """
        Create a window opening.

        Args:
            wall_start: Wall start point
            wall_end: Wall end point
            window: Window specification
        """
        # Calculate window position along the wall
        dx = wall_end[0] - wall_start[0]
        dy = wall_end[1] - wall_start[1]

        window_center_x = wall_start[0] + dx * window.position
        window_center_y = wall_start[1] + dy * window.position

        # Calculate window opening points
        wall_length = math.sqrt(dx**2 + dy**2)
        unit_dx = dx / wall_length
        unit_dy = dy / wall_length

        half_width = window.width / 2
        opening_start = (
            window_center_x - unit_dx * half_width,
            window_center_y - unit_dy * half_width
        )
        opening_end = (
            window_center_x + unit_dx * half_width,
            window_center_y + unit_dy * half_width
        )

        # Draw window opening (double line for glass)
        self.msp.add_line(opening_start, opening_end, dxfattribs={"layer": "WINDOW"})

        # Draw window sill line (slightly offset)
        perp_x = -unit_dy * 0.05
        perp_y = unit_dx * 0.05

        sill_start = (opening_start[0] + perp_x, opening_start[1] + perp_y)
        sill_end = (opening_end[0] + perp_x, opening_end[1] + perp_y)

        self.msp.add_line(sill_start, sill_end, dxfattribs={"layer": "WINDOW"})

    def create_furniture(self, furniture: Furniture) -> None:
        """
        Create a furniture item as a simple rectangle.

        Args:
            furniture: Furniture specification
        """
        if not furniture.dimensions:
            # Default dimensions based on furniture type
            default_dims = {
                "bed": (2.0, 1.5, 0.5),
                "desk": (1.2, 0.6, 0.75),
                "sofa": (2.0, 0.9, 0.85),
                "table": (1.5, 0.9, 0.75),
            }
            width, depth, height = default_dims.get(furniture.type.value, (1.0, 1.0, 0.5))
        else:
            width = furniture.dimensions.width or 1.0
            depth = furniture.dimensions.depth or 1.0

        # Create rectangle centered at position
        half_w = width / 2
        half_d = depth / 2

        # Rotation
        angle_rad = math.radians(furniture.position.rotation)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Rectangle corners before rotation
        corners = [
            (-half_w, -half_d),
            (half_w, -half_d),
            (half_w, half_d),
            (-half_w, half_d),
            (-half_w, -half_d)  # Close the rectangle
        ]

        # Rotate and translate corners
        rotated_corners = []
        for x, y in corners:
            rotated_x = x * cos_a - y * sin_a + furniture.position.x
            rotated_y = x * sin_a + y * cos_a + furniture.position.y
            rotated_corners.append((rotated_x, rotated_y))

        # Draw polyline
        self.msp.add_lwpolyline(
            rotated_corners,
            dxfattribs={"layer": "FURNITURE"}
        )

        # Add label
        if furniture.label:
            self.msp.add_text(
                furniture.label,
                dxfattribs={
                    "layer": "TEXT",
                    "height": 0.2
                }
            ).set_placement(
                (furniture.position.x, furniture.position.y),
                align=TextEntityAlignment.MIDDLE_CENTER
            )

    def create_room(self, room: Room) -> None:
        """
        Create a complete room with walls, doors, windows, and furniture.

        Args:
            room: Room specification
        """
        coords = room.geometry.coordinates

        # Ensure the polygon is closed
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        # Create walls
        for i in range(len(coords) - 1):
            start = tuple(coords[i])
            end = tuple(coords[i + 1])
            self.create_wall(start, end)

        # Create doors
        if room.doors:
            for door in room.doors:
                if door.wall_index < len(coords) - 1:
                    wall_start = tuple(coords[door.wall_index])
                    wall_end = tuple(coords[door.wall_index + 1])
                    self.create_door(wall_start, wall_end, door)

        # Create windows
        if room.windows:
            for window in room.windows:
                if window.wall_index < len(coords) - 1:
                    wall_start = tuple(coords[window.wall_index])
                    wall_end = tuple(coords[window.wall_index + 1])
                    self.create_window(wall_start, wall_end, window)

        # Create furniture
        if room.furniture:
            for furn in room.furniture:
                self.create_furniture(furn)

        # Add room label
        # Calculate room center
        center_x = sum(c[0] for c in coords[:-1]) / (len(coords) - 1)
        center_y = sum(c[1] for c in coords[:-1]) / (len(coords) - 1)

        self.msp.add_text(
            room.name,
            dxfattribs={
                "layer": "TEXT",
                "height": 0.3
            }
        ).set_placement(
            (center_x, center_y),
            align=TextEntityAlignment.MIDDLE_CENTER
        )

    def create_floor_plan(self, spec: DesignSpec, floor_level: int = 1) -> None:
        """
        Create a complete floor plan from design specification.

        Args:
            spec: Complete design specification
            floor_level: Which floor to generate (1-based)
        """
        # Find the requested floor
        target_floor = None
        for floor in spec.building.floors:
            if floor.level == floor_level:
                target_floor = floor
                break

        if not target_floor:
            raise ValueError(f"Floor level {floor_level} not found in specification")

        # Create new document if not exists
        if self.doc is None:
            self.create_new_document()

        # Add title block
        self._add_title_block(spec, target_floor)

        # Create all rooms
        for room in target_floor.rooms:
            self.create_room(room)

    def _add_title_block(self, spec: DesignSpec, floor) -> None:
        """Add title block with project information."""
        # Simple title block in upper right
        title_x = 20
        title_y = 15

        texts = [
            (spec.project_info.name, 0.5),
            (f"Level {floor.level}", 0.3),
            (spec.project_info.client or "", 0.2),
        ]

        y_offset = title_y
        for text, height in texts:
            if text:
                self.msp.add_text(
                    text,
                    dxfattribs={
                        "layer": "TEXT",
                        "height": height
                    }
                ).set_placement(
                    (title_x, y_offset),
                    align=TextEntityAlignment.TOP_LEFT
                )
                y_offset -= height * 1.5

    def save(self, output_path: Path) -> None:
        """
        Save the DXF document to file.

        Args:
            output_path: Output file path
        """
        if self.doc is None:
            raise ValueError("No document to save. Create a document first.")

        self.doc.saveas(output_path)

    def generate_from_spec(self, spec: DesignSpec, output_path: Path, floor_level: int = 1) -> Path:
        """
        Complete workflow: Generate DXF from specification and save.

        Args:
            spec: Design specification
            output_path: Output file path
            floor_level: Floor level to generate

        Returns:
            Path to generated DXF file
        """
        self.create_floor_plan(spec, floor_level)
        self.save(output_path)
        return output_path
