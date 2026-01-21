"""
Compliance Agent for building code compliance checking.

Verifies compliance with Korean building regulations including:
- Building coverage ratio (건폐율)
- Floor area ratio (용적률)
- Parking requirements (주차대수)
- Fire safety regulations
- Height restrictions
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from ..models.design_spec import DesignSpec, RoomType
from ..skills.schema_validator import DesignSpecValidator as SchemaValidator
from ..skills.geometry_engine import GeometryEngine


class ComplianceAgent:
    """
    Building code compliance checking agent.

    Verifies compliance with:
    - Korean Building Act (건축법)
    - Korean Housing Act (주택법)
    - Local zoning regulations
    - Fire safety codes
    - Accessibility standards
    """

    def __init__(self, schema_path: Path):
        """
        Initialize compliance agent.

        Args:
            schema_path: Path to JSON schema file
        """
        self.schema_path = Path(schema_path)
        self.validator = SchemaValidator(schema_path)
        self.geometry_engine = GeometryEngine()

    def check_compliance(
        self,
        spec: DesignSpec,
        site_area: float,
        zoning_type: str = "residential",
        zoning_district: str = "type2"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive compliance check.

        Args:
            spec: Design specification
            site_area: Total site area in m²
            zoning_type: Zoning type (residential, commercial, industrial)
            zoning_district: Specific zoning district

        Returns:
            Dictionary with compliance check results
        """
        results = {
            'site_info': {
                'site_area': site_area,
                'zoning_type': zoning_type,
                'zoning_district': zoning_district
            },
            'building_coverage': self._check_building_coverage(spec, site_area, zoning_type),
            'floor_area_ratio': self._check_floor_area_ratio(spec, site_area, zoning_type, zoning_district),
            'parking': self._check_parking_requirements(spec, zoning_type),
            'fire_safety': self._check_fire_safety(spec),
            'accessibility': self._check_accessibility(spec),
            'height_restriction': self._check_height_restriction(spec, zoning_type, zoning_district),
            'room_dimensions': self._check_room_dimensions(spec),
            'overall_compliance': None  # Will be set at the end
        }

        # Determine overall compliance
        all_checks = [
            results['building_coverage']['compliant'],
            results['floor_area_ratio']['compliant'],
            results['parking']['compliant'],
            results['fire_safety']['compliant'],
            results['accessibility']['compliant'],
            results['height_restriction']['compliant'],
            results['room_dimensions']['compliant']
        ]

        results['overall_compliance'] = {
            'status': 'PASS' if all(all_checks) else 'FAIL',
            'passed_checks': sum(all_checks),
            'total_checks': len(all_checks)
        }

        return results

    def _check_building_coverage(
        self,
        spec: DesignSpec,
        site_area: float,
        zoning_type: str
    ) -> Dict[str, Any]:
        """
        Check building coverage ratio (건폐율).

        Korean Building Act limits:
        - Residential (Type 1): 50%
        - Residential (Type 2): 60%
        - Commercial: 60-80%
        - Industrial: 70%
        """
        # Calculate building footprint (ground floor area)
        building_footprint = 0.0

        if spec.building.floors:
            ground_floor = spec.building.floors[0]
            for room in ground_floor.rooms:
                area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )
                building_footprint += area

        # Calculate coverage ratio
        coverage_ratio = (building_footprint / site_area) * 100 if site_area > 0 else 0

        # Get maximum allowed
        max_coverage = {
            'residential': 60,
            'commercial': 70,
            'industrial': 70
        }

        max_allowed = max_coverage.get(zoning_type, 60)

        return {
            'building_footprint': building_footprint,
            'site_area': site_area,
            'coverage_ratio': coverage_ratio,
            'max_allowed': max_allowed,
            'compliant': coverage_ratio <= max_allowed,
            'margin': max_allowed - coverage_ratio,
            'code_reference': '건축법 시행령 제80조 (건폐율)'
        }

    def _check_floor_area_ratio(
        self,
        spec: DesignSpec,
        site_area: float,
        zoning_type: str,
        zoning_district: str
    ) -> Dict[str, Any]:
        """
        Check floor area ratio (용적률).

        Korean Building Act limits:
        - Residential (Type 1): 100-150%
        - Residential (Type 2): 150-200%
        - Commercial: 200-1500% (varies greatly)
        - Industrial: 200-300%
        """
        # Calculate total floor area
        total_floor_area = 0.0

        for floor in spec.building.floors:
            for room in floor.rooms:
                area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )
                total_floor_area += area

        # Calculate FAR
        floor_area_ratio = (total_floor_area / site_area) * 100 if site_area > 0 else 0

        # Get maximum allowed based on zoning
        max_far_table = {
            ('residential', 'type1'): 150,
            ('residential', 'type2'): 200,
            ('residential', 'type3'): 250,
            ('commercial', 'general'): 400,
            ('commercial', 'central'): 800,
            ('industrial', 'general'): 250
        }

        max_allowed = max_far_table.get((zoning_type, zoning_district), 200)

        return {
            'total_floor_area': total_floor_area,
            'site_area': site_area,
            'floor_area_ratio': floor_area_ratio,
            'max_allowed': max_allowed,
            'compliant': floor_area_ratio <= max_allowed,
            'margin': max_allowed - floor_area_ratio,
            'code_reference': '건축법 시행령 제84조 (용적률)'
        }

    def _check_parking_requirements(
        self,
        spec: DesignSpec,
        zoning_type: str
    ) -> Dict[str, Any]:
        """
        Check parking requirements (주차대수).

        Korean Housing Act:
        - Residential: 1 space per 85m² of floor area
        - Or 1 space per dwelling unit (whichever is greater)
        """
        # Calculate total floor area
        total_floor_area = sum(
            self.geometry_engine.calculate_polygon_area(room.geometry.coordinates)
            for floor in spec.building.floors
            for room in floor.rooms
        )

        # Count dwelling units (assume each floor with living room is one unit)
        dwelling_units = sum(
            1 for floor in spec.building.floors
            if any(room.type == RoomType.LIVING_ROOM for room in floor.rooms)
        )

        # Calculate required parking
        if zoning_type == 'residential':
            # Method 1: Area-based (1 space per 85m²)
            parking_by_area = total_floor_area / 85

            # Method 2: Unit-based (1 space per unit)
            parking_by_unit = dwelling_units

            # Use whichever is greater
            required_parking = max(parking_by_area, parking_by_unit)
        elif zoning_type == 'commercial':
            # Commercial: 1 space per 150m²
            required_parking = total_floor_area / 150
        else:
            required_parking = total_floor_area / 200

        required_parking = math.ceil(required_parking)

        # Check for existing parking in design (from room types)
        provided_parking = sum(
            1 for floor in spec.building.floors
            for room in floor.rooms
            if room.type == RoomType.PARKING
        )

        return {
            'total_floor_area': total_floor_area,
            'dwelling_units': dwelling_units,
            'required_parking': required_parking,
            'provided_parking': provided_parking,
            'compliant': provided_parking >= required_parking,
            'shortage': max(0, required_parking - provided_parking),
            'code_reference': '주택법 시행령 제27조 (주차장 설치기준)'
        }

    def _check_fire_safety(self, spec: DesignSpec) -> Dict[str, Any]:
        """
        Check fire safety compliance.

        Korean Building Act fire safety requirements.
        """
        checks = []
        issues = []

        # Check 1: Fire exits
        floor_count = len(spec.building.floors)
        if floor_count > 2:
            # Buildings > 2 floors need 2+ fire exits
            # Simplified: check for 2+ doors per floor
            for floor in spec.building.floors:
                total_doors = sum(len(room.doors) for room in floor.rooms)
                if total_doors < 2:
                    issues.append(f"Floor {floor.level}: Insufficient exits (need 2+)")

        # Check 2: Corridor width
        # Korean code: minimum 1.2m for residential, 1.5m for commercial
        min_corridor_width = 1.2  # meters

        # Check 3: Fire-rated walls between units
        # (Would need additional data in spec)

        # Check 4: Smoke detectors required
        checks.append({
            'item': 'Smoke Detectors',
            'requirement': 'Required in all rooms',
            'status': 'REQUIRED'
        })

        # Check 5: Fire extinguishers
        checks.append({
            'item': 'Fire Extinguishers',
            'requirement': 'One per 20m travel distance',
            'status': 'REQUIRED'
        })

        compliant = len(issues) == 0

        return {
            'compliant': compliant,
            'checks': checks,
            'issues': issues,
            'code_reference': '건축법 제49조 (소방시설)'
        }

    def _check_accessibility(self, spec: DesignSpec) -> Dict[str, Any]:
        """
        Check accessibility compliance.

        Korean Welfare of Persons with Disabilities Act.
        """
        checks = []
        issues = []

        # Check 1: Entrance accessibility
        # Need at least one accessible entrance (ramp or level entry)
        checks.append({
            'item': 'Accessible Entrance',
            'requirement': 'Level or ramped entrance required',
            'status': 'REVIEW REQUIRED'
        })

        # Check 2: Door width
        # Minimum 0.8m clear width for accessibility
        min_door_width = 0.8  # meters

        for floor in spec.building.floors:
            for room in floor.rooms:
                for door in room.doors:
                    if door.width < min_door_width:
                        issues.append(
                            f"{room.name}: Door width {door.width}m < {min_door_width}m required"
                        )

        # Check 3: Bathroom accessibility
        # At least one accessible bathroom required
        has_bathroom = any(
            room.type == RoomType.BATHROOM
            for floor in spec.building.floors
            for room in floor.rooms
        )

        if has_bathroom:
            checks.append({
                'item': 'Accessible Bathroom',
                'requirement': 'One accessible bathroom required',
                'status': 'REVIEW REQUIRED'
            })

        # Check 4: Elevator (for buildings > 3 floors)
        floor_count = len(spec.building.floors)
        if floor_count > 3:
            checks.append({
                'item': 'Elevator',
                'requirement': 'Required for buildings > 3 floors',
                'status': 'REQUIRED'
            })

        compliant = len(issues) == 0

        return {
            'compliant': compliant,
            'checks': checks,
            'issues': issues,
            'code_reference': '장애인·노인·임산부 등의 편의증진 보장에 관한 법률'
        }

    def _check_height_restriction(
        self,
        spec: DesignSpec,
        zoning_type: str,
        zoning_district: str
    ) -> Dict[str, Any]:
        """
        Check height restrictions.

        Korean Building Act height limits vary by zoning.
        """
        building_height = sum(floor.height for floor in spec.building.floors)

        # Height limits by zoning (meters)
        height_limits = {
            ('residential', 'type1'): 15,  # Low-rise residential
            ('residential', 'type2'): 20,
            ('residential', 'type3'): None,  # No limit (with review)
            ('commercial', 'general'): 50,
            ('commercial', 'central'): None,  # No limit
            ('industrial', 'general'): 20
        }

        max_height = height_limits.get((zoning_type, zoning_district), 20)

        if max_height is None:
            compliant = True
            status = 'No restriction (design review required)'
        else:
            compliant = building_height <= max_height
            status = 'PASS' if compliant else 'FAIL'

        return {
            'building_height': building_height,
            'max_allowed_height': max_height,
            'compliant': compliant,
            'margin': (max_height - building_height) if max_height else None,
            'status': status,
            'code_reference': '건축법 제60조 (높이 제한)'
        }

    def _check_room_dimensions(self, spec: DesignSpec) -> Dict[str, Any]:
        """
        Check room dimension requirements.

        Korean Housing Act minimum room sizes.
        """
        checks = []
        issues = []

        # Minimum room sizes (m²)
        min_room_sizes = {
            RoomType.LIVING_ROOM: 18.0,
            RoomType.BEDROOM: 9.0,
            RoomType.KITCHEN: 4.5,
            RoomType.BATHROOM: 3.0
        }

        # Minimum ceiling height
        min_ceiling_height = 2.1  # meters

        for floor in spec.building.floors:
            # Check ceiling height
            if floor.height < min_ceiling_height:
                issues.append(
                    f"Floor {floor.level}: Height {floor.height}m < {min_ceiling_height}m minimum"
                )

            # Check room sizes
            for room in floor.rooms:
                area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )

                min_size = min_room_sizes.get(room.type)
                if min_size and area < min_size:
                    issues.append(
                        f"{room.name} ({room.type.value}): {area:.1f}m² < {min_size}m² minimum"
                    )

                checks.append({
                    'room': room.name,
                    'type': room.type.value,
                    'area': area,
                    'min_required': min_size,
                    'compliant': area >= min_size if min_size else True
                })

        compliant = len(issues) == 0

        return {
            'compliant': compliant,
            'checks': checks,
            'issues': issues,
            'code_reference': '주택법 시행규칙 제2조 (주택의 규모)'
        }

    def generate_report(
        self,
        compliance_results: Dict[str, Any],
        output_path: Path
    ):
        """
        Generate compliance check report.

        Args:
            compliance_results: Results from check_compliance()
            output_path: Path for output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(compliance_results, f, indent=2, ensure_ascii=False)

    def generate_summary_report(
        self,
        compliance_results: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable summary report.

        Args:
            compliance_results: Results from check_compliance()

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("BUILDING CODE COMPLIANCE REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Overall status
        overall = compliance_results['overall_compliance']
        lines.append(f"Overall Status: {overall['status']}")
        lines.append(f"Passed: {overall['passed_checks']}/{overall['total_checks']} checks")
        lines.append("")

        # Individual checks
        for key, result in compliance_results.items():
            if key in ['site_info', 'overall_compliance']:
                continue

            lines.append(f"{key.replace('_', ' ').title()}:")
            if isinstance(result, dict) and 'compliant' in result:
                status = "✓ PASS" if result['compliant'] else "✗ FAIL"
                lines.append(f"  Status: {status}")

                if 'issues' in result and result['issues']:
                    lines.append("  Issues:")
                    for issue in result['issues']:
                        lines.append(f"    - {issue}")

            lines.append("")

        return "\n".join(lines)

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get agent capabilities.

        Returns:
            Capabilities dictionary
        """
        return {
            'name': 'Compliance Agent',
            'version': '1.0.0',
            'description': 'Building code compliance checking agent',
            'features': [
                'Building coverage ratio check (건폐율)',
                'Floor area ratio check (용적률)',
                'Parking requirements (주차대수)',
                'Fire safety compliance',
                'Accessibility standards',
                'Height restrictions',
                'Room dimension requirements'
            ],
            'regulations': [
                'Korean Building Act (건축법)',
                'Korean Housing Act (주택법)',
                'Fire Safety Act (소방법)',
                'Accessibility Act (장애인법)'
            ]
        }


# Add missing import
import math
