"""
Revit Agent for BIM model generation.

Generates IFC (Industry Foundation Classes) files from DesignSpec JSON.
IFC is the international standard for BIM data exchange.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json

try:
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.geom
    import ifcopenshell.util
    from ifcopenshell.api import run
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

from ..models.design_spec import DesignSpec, Room, Door, Window
from ..skills.schema_validator import DesignSpecValidator as SchemaValidator
from ..skills.geometry_engine import GeometryEngine


class RevitAgent:
    """
    Revit/BIM agent for generating IFC files.

    This agent converts DesignSpec JSON into IFC (Industry Foundation Classes)
    format, which can be opened in Revit, ArchiCAD, and other BIM software.

    Capabilities:
    - Generate 3D building models
    - Create walls with thickness
    - Place doors and windows
    - Add spaces/rooms
    - Export to IFC 2x3 or IFC4 format
    """

    def __init__(self, schema_path: Path):
        """
        Initialize Revit agent.

        Args:
            schema_path: Path to JSON schema file
        """
        if not IFC_AVAILABLE:
            raise ImportError(
                "ifcopenshell not installed. Install with: pip install ifcopenshell"
            )

        self.schema_path = Path(schema_path)
        self.validator = SchemaValidator(schema_path)
        self.geometry_engine = GeometryEngine()

        # IFC model
        self.ifc_file = None
        self.project = None
        self.site = None
        self.building = None
        self.storey = None

    def create_bim_model(
        self,
        spec: DesignSpec,
        output_path: Path,
        ifc_schema: str = "IFC4"
    ):
        """
        Create BIM model from DesignSpec.

        Args:
            spec: Design specification
            output_path: Path for output IFC file
            ifc_schema: IFC schema version ("IFC2X3" or "IFC4")
        """
        # Initialize IFC file
        self.ifc_file = ifcopenshell.file(schema=ifc_schema)

        # Create project hierarchy
        self._create_project_hierarchy(spec)

        # Generate building elements
        for floor in spec.building.floors:
            self._create_storey(floor)

            for room in floor.rooms:
                self._create_room_elements(room, floor.height)

        # Write to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.ifc_file.write(str(output_path))

    def _create_project_hierarchy(self, spec: DesignSpec):
        """
        Create IFC project hierarchy.

        Hierarchy: Project → Site → Building → Storey → Space
        """
        # Create units (metric)
        run("unit.assign_unit", self.ifc_file)

        # Create project
        self.project = run("root.create_entity", self.ifc_file, ifc_class="IfcProject",
                          name=spec.project_info.name)

        # Create site
        self.site = run("root.create_entity", self.ifc_file, ifc_class="IfcSite",
                       name="Site")
        run("aggregate.assign_object", self.ifc_file,
            product=self.site, relating_object=self.project)

        # Create building
        self.building = run("root.create_entity", self.ifc_file, ifc_class="IfcBuilding",
                           name="Building")
        run("aggregate.assign_object", self.ifc_file,
            product=self.building, relating_object=self.site)

    def _create_storey(self, floor):
        """Create building storey."""
        self.storey = run("root.create_entity", self.ifc_file, ifc_class="IfcBuildingStorey",
                         name=f"Level {floor.level}")

        # Set elevation
        run("aggregate.assign_object", self.ifc_file,
            product=self.storey, relating_object=self.building)

    def _create_room_elements(self, room: Room, floor_height: float):
        """
        Create room elements (walls, doors, windows, space).

        Args:
            room: Room specification
            floor_height: Height of the floor
        """
        # Create space
        space = run("root.create_entity", self.ifc_file, ifc_class="IfcSpace",
                   name=room.name)
        run("spatial.assign_container", self.ifc_file,
            product=space, relating_structure=self.storey)

        # Create walls
        wall_thickness = 0.2  # 20cm default
        coords = room.geometry.coordinates

        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i + 1]

            # Skip zero-length segments
            if p1 == p2:
                continue

            wall = self._create_wall(p1, p2, floor_height, wall_thickness)

            # Add doors on this wall
            for door in room.doors:
                if door.wall_index == i:
                    self._create_door(wall, door, p1, p2, floor_height)

            # Add windows on this wall
            for window in room.windows:
                if window.wall_index == i:
                    self._create_window(wall, window, p1, p2, floor_height)

    def _create_wall(
        self,
        start_point: List[float],
        end_point: List[float],
        height: float,
        thickness: float
    ):
        """Create a wall element."""
        wall = run("root.create_entity", self.ifc_file, ifc_class="IfcWall")
        run("spatial.assign_container", self.ifc_file,
            product=wall, relating_structure=self.storey)

        # Create wall geometry
        # Note: Simplified implementation - real implementation would create
        # proper IfcExtrudedAreaSolid geometry

        return wall

    def _create_door(
        self,
        wall,
        door: Door,
        wall_start: List[float],
        wall_end: List[float],
        floor_height: float
    ):
        """Create a door element."""
        door_elem = run("root.create_entity", self.ifc_file, ifc_class="IfcDoor")
        run("spatial.assign_container", self.ifc_file,
            product=door_elem, relating_structure=self.storey)

        # TODO: Position door on wall, create opening

        return door_elem

    def _create_window(
        self,
        wall,
        window: Window,
        wall_start: List[float],
        wall_end: List[float],
        floor_height: float
    ):
        """Create a window element."""
        window_elem = run("root.create_entity", self.ifc_file, ifc_class="IfcWindow")
        run("spatial.assign_container", self.ifc_file,
            product=window_elem, relating_structure=self.storey)

        # TODO: Position window on wall, create opening

        return window_elem

    def create_bim_model_from_json(
        self,
        json_path: Path,
        output_path: Path,
        ifc_schema: str = "IFC4"
    ):
        """
        Create BIM model from JSON file.

        Args:
            json_path: Path to JSON specification
            output_path: Path for output IFC file
            ifc_schema: IFC schema version
        """
        # Load and validate JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            spec_dict = json.load(f)

        validation_result = self.validator.validate_all(spec_dict)
        if not validation_result['valid']:
            raise ValueError(f"Invalid specification: {validation_result['errors']}")

        # Convert to model
        spec = DesignSpec(**spec_dict)

        # Create BIM model
        self.create_bim_model(spec, output_path, ifc_schema)

    def analyze_bim_model(self, spec: DesignSpec) -> Dict[str, Any]:
        """
        Analyze BIM model and return statistics.

        Args:
            spec: Design specification

        Returns:
            Dictionary with model statistics
        """
        total_volume = 0.0
        total_floor_area = 0.0
        total_walls = 0
        total_doors = 0
        total_windows = 0

        for floor in spec.building.floors:
            floor_area = 0.0

            for room in floor.rooms:
                # Calculate room volume
                area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )
                volume = area * floor.height

                total_volume += volume
                floor_area += area
                total_floor_area += area

                # Count elements
                total_walls += len(room.geometry.coordinates) - 1
                total_doors += len(room.doors)
                total_windows += len(room.windows)

        return {
            'total_floors': len(spec.building.floors),
            'total_rooms': sum(len(f.rooms) for f in spec.building.floors),
            'total_floor_area': total_floor_area,
            'total_volume': total_volume,
            'total_walls': total_walls,
            'total_doors': total_doors,
            'total_windows': total_windows,
            'building_height': sum(f.height for f in spec.building.floors)
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get agent capabilities.

        Returns:
            Capabilities dictionary
        """
        return {
            'name': 'Revit Agent',
            'version': '1.0.0',
            'description': 'BIM model generation agent',
            'supported_formats': ['IFC'],
            'ifc_schemas': ['IFC2X3', 'IFC4'],
            'features': [
                'Generate 3D BIM models',
                'Create walls, doors, windows',
                'Define building spaces',
                'Export to IFC format',
                'Compatible with Revit, ArchiCAD, etc.'
            ],
            'library': 'ifcopenshell',
            'library_available': IFC_AVAILABLE
        }


# Simplified implementation note:
# This is a basic implementation that creates IFC entities.
# A full production implementation would include:
# - Proper 3D geometry (IfcExtrudedAreaSolid, IfcPolyline, etc.)
# - Material assignments (IfcMaterial, IfcMaterialLayerSet)
# - Property sets (IfcPropertySet)
# - Relationships (IfcRelContainedInSpatialStructure, IfcRelFillsElement)
# - Precise door/window openings (IfcOpeningElement)
# - Quantity take-offs (IfcElementQuantity)
# - Structural elements (IfcBeam, IfcColumn, IfcSlab)
