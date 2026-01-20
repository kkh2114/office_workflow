"""
Schema Validator Skill
Validates design specifications against JSON schema.
"""

import json
from pathlib import Path
from typing import Tuple, List, Dict, Any
from jsonschema import validate, ValidationError, Draft7Validator

from ..models.design_spec import DesignSpec


class DesignSpecValidator:
    """Validates architectural design specifications."""

    def __init__(self, schema_path: Path):
        """
        Initialize validator with JSON schema.

        Args:
            schema_path: Path to JSON schema file
        """
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)

        self.validator = Draft7Validator(self.schema)

    def validate_json(self, spec_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a specification dictionary against the schema.

        Args:
            spec_dict: Design specification as dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            validate(instance=spec_dict, schema=self.schema)
            return True, []
        except ValidationError as e:
            errors.append(f"Validation error: {e.message}")
            errors.append(f"Path: {' -> '.join(str(p) for p in e.path)}")

            # Collect all validation errors
            for error in self.validator.iter_errors(spec_dict):
                errors.append(f"  - {error.message} at {'.'.join(str(p) for p in error.path)}")

            return False, errors

    def validate_model(self, spec: DesignSpec) -> Tuple[bool, List[str]]:
        """
        Validate a Pydantic DesignSpec model.

        Args:
            spec: DesignSpec model instance

        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            # Pydantic models are already validated, but we can add custom checks
            errors = []

            # Check for closed polygons
            for floor in spec.building.floors:
                for room in floor.rooms:
                    coords = room.geometry.coordinates
                    if coords[0] != coords[-1]:
                        errors.append(
                            f"Room '{room.name}' polygon is not closed. "
                            f"First point {coords[0]} != Last point {coords[-1]}"
                        )

            # Check door/window indices
            for floor in spec.building.floors:
                for room in floor.rooms:
                    num_walls = len(room.geometry.coordinates) - 1

                    if room.doors:
                        for i, door in enumerate(room.doors):
                            if door.wall_index >= num_walls:
                                errors.append(
                                    f"Room '{room.name}' door {i}: wall_index {door.wall_index} "
                                    f"exceeds number of walls ({num_walls})"
                                )

                    if room.windows:
                        for i, window in enumerate(room.windows):
                            if window.wall_index >= num_walls:
                                errors.append(
                                    f"Room '{room.name}' window {i}: wall_index {window.wall_index} "
                                    f"exceeds number of walls ({num_walls})"
                                )

            if errors:
                return False, errors

            return True, []

        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    def validate_geometry(self, spec: DesignSpec) -> Tuple[bool, List[str]]:
        """
        Validate geometric properties of the specification.

        Args:
            spec: DesignSpec model instance

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        for floor in spec.building.floors:
            for room in floor.rooms:
                coords = room.geometry.coordinates

                # Check minimum number of points
                if len(coords) < 4:  # 3 points + closing point
                    errors.append(
                        f"Room '{room.name}' has insufficient points ({len(coords)}). "
                        f"Minimum 4 points required (3 + closing point)"
                    )

                # Check for degenerate segments (zero-length walls)
                for i in range(len(coords) - 1):
                    p1 = coords[i]
                    p2 = coords[i + 1]
                    if p1 == p2:
                        errors.append(
                            f"Room '{room.name}' has zero-length wall segment at index {i}"
                        )

        if errors:
            return False, errors

        return True, []

    def full_validation(self, spec: DesignSpec) -> Tuple[bool, List[str]]:
        """
        Perform complete validation: schema, model, and geometry.

        Args:
            spec: DesignSpec model instance

        Returns:
            Tuple of (is_valid, error_messages)
        """
        all_errors = []

        # Validate model
        valid_model, model_errors = self.validate_model(spec)
        if not valid_model:
            all_errors.extend(["Model validation errors:"] + model_errors)

        # Validate geometry
        valid_geom, geom_errors = self.validate_geometry(spec)
        if not valid_geom:
            all_errors.extend(["Geometry validation errors:"] + geom_errors)

        is_valid = valid_model and valid_geom

        return is_valid, all_errors
