"""
AutoCAD Agent
Implementation agent responsible for generating AutoCAD DXF/DWG files.
"""

import logging
from pathlib import Path
from typing import Optional
import json

from ..models.design_spec import DesignSpec
from ..skills.dxf_generator import DXFGenerator
from ..skills.schema_validator import DesignSpecValidator
from ..skills.geometry_engine import GeometryEngine


class AutoCADAgent:
    """
    AutoCAD Implementation Agent.
    Generates 2D floor plans in DXF format from design specifications.
    """

    def __init__(
        self,
        wall_thickness: float = 0.2,
        schema_path: Optional[Path] = None
    ):
        """
        Initialize AutoCAD Agent.

        Args:
            wall_thickness: Default wall thickness in meters
            schema_path: Path to JSON schema file for validation
        """
        self.logger = logging.getLogger(__name__)
        self.dxf_generator = DXFGenerator(wall_thickness=wall_thickness)
        self.geometry_engine = GeometryEngine()

        # Initialize validator if schema path provided
        self.validator = None
        if schema_path and schema_path.exists():
            self.validator = DesignSpecValidator(schema_path)

    def create_floor_plan(
        self,
        spec: DesignSpec,
        output_path: Path,
        floor_level: int = 1,
        validate: bool = True
    ) -> Path:
        """
        Create a floor plan DXF file from design specification.

        Args:
            spec: Design specification
            output_path: Output DXF file path
            floor_level: Floor level to generate (1-based)
            validate: Whether to validate specification before generation

        Returns:
            Path to generated DXF file

        Raises:
            ValueError: If validation fails or floor not found
        """
        self.logger.info(f"Creating floor plan for level {floor_level}")

        # Validate specification
        if validate and self.validator:
            is_valid, errors = self.validator.full_validation(spec)
            if not is_valid:
                error_msg = "Specification validation failed:\n" + "\n".join(errors)
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate DXF
        try:
            result_path = self.dxf_generator.generate_from_spec(
                spec=spec,
                output_path=output_path,
                floor_level=floor_level
            )

            self.logger.info(f"Floor plan generated successfully: {result_path}")
            return result_path

        except Exception as e:
            self.logger.error(f"Error generating floor plan: {str(e)}")
            raise

    def create_floor_plan_from_json(
        self,
        json_path: Path,
        output_path: Path,
        floor_level: int = 1
    ) -> Path:
        """
        Create a floor plan from JSON specification file.

        Args:
            json_path: Path to JSON specification file
            output_path: Output DXF file path
            floor_level: Floor level to generate

        Returns:
            Path to generated DXF file
        """
        self.logger.info(f"Loading specification from {json_path}")

        # Load JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            spec_dict = json.load(f)

        # Parse into Pydantic model
        spec = DesignSpec(**spec_dict)

        # Generate floor plan
        return self.create_floor_plan(spec, output_path, floor_level)

    def analyze_floor_plan(self, spec: DesignSpec, floor_level: int = 1) -> dict:
        """
        Analyze a floor plan and return statistics.

        Args:
            spec: Design specification
            floor_level: Floor level to analyze

        Returns:
            Dictionary containing floor plan statistics
        """
        # Find the requested floor
        target_floor = None
        for floor in spec.building.floors:
            if floor.level == floor_level:
                target_floor = floor
                break

        if not target_floor:
            raise ValueError(f"Floor level {floor_level} not found")

        stats = {
            "floor_level": floor_level,
            "num_rooms": len(target_floor.rooms),
            "total_area": 0,
            "rooms": []
        }

        for room in target_floor.rooms:
            # Calculate room area
            area = self.geometry_engine.calculate_polygon_area(room.geometry.coordinates)

            # Calculate perimeter
            perimeter = self.geometry_engine.calculate_polygon_perimeter(room.geometry.coordinates)

            # Calculate centroid
            centroid = self.geometry_engine.calculate_centroid(room.geometry.coordinates)

            room_stats = {
                "name": room.name,
                "type": room.type.value if room.type else None,
                "area": round(area, 2),
                "perimeter": round(perimeter, 2),
                "centroid": centroid,
                "num_doors": len(room.doors) if room.doors else 0,
                "num_windows": len(room.windows) if room.windows else 0,
                "num_furniture": len(room.furniture) if room.furniture else 0
            }

            stats["rooms"].append(room_stats)
            stats["total_area"] += area

        stats["total_area"] = round(stats["total_area"], 2)

        return stats

    def analyze_floor_plan_from_json(
        self,
        json_path: Path,
        floor_level: int = 1
    ) -> dict:
        """
        Analyze floor plan from JSON file.

        Args:
            json_path: Path to JSON specification
            floor_level: Floor level to analyze (default: 1)

        Returns:
            Dictionary with analysis statistics
        """
        import json

        # Load JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            spec_dict = json.load(f)

        # Convert to DesignSpec
        spec = DesignSpec(**spec_dict)

        # Analyze
        return self.analyze_floor_plan(spec, floor_level)

    def validate_specification(self, spec: DesignSpec) -> tuple[bool, list[str]]:
        """
        Validate a design specification.

        Args:
            spec: Design specification to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not self.validator:
            return True, ["No validator configured"]

        return self.validator.full_validation(spec)

    def get_capabilities(self) -> dict:
        """
        Get agent capabilities.

        Returns:
            Dictionary describing agent capabilities
        """
        return {
            "name": "AutoCADAgent",
            "description": "Generates 2D floor plans in DXF format",
            "supported_formats": ["DXF"],
            "dxf_version": "R2018",
            "features": [
                "Floor plan generation",
                "Wall creation with thickness",
                "Door and window placement",
                "Furniture layout",
                "Room labeling",
                "Title block",
                "Layer management"
            ],
            "limitations": [
                "2D only (no 3D modeling)",
                "Single floor per file",
                "No structural analysis",
                "No MEP systems"
            ]
        }
