"""
Structural Agent for structural design and load calculations.

Performs structural analysis including:
- Load calculations (dead load, live load, wind load)
- Column and beam sizing
- Foundation design (preliminary)
- Structural member layout
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json
import math

from ..models.design_spec import DesignSpec, Floor, Room
from ..skills.schema_validator import DesignSpecValidator as SchemaValidator
from ..skills.geometry_engine import GeometryEngine


class StructuralAgent:
    """
    Structural design agent for buildings.

    Capabilities:
    - Calculate dead loads and live loads
    - Size structural members (columns, beams)
    - Generate structural grid
    - Preliminary foundation design
    - Korean building code compliance
    - Generate structural layout drawings
    """

    def __init__(self, schema_path: Path):
        """
        Initialize structural agent.

        Args:
            schema_path: Path to JSON schema file
        """
        self.schema_path = Path(schema_path)
        self.validator = SchemaValidator(schema_path)
        self.geometry_engine = GeometryEngine()

        # Material properties (default: concrete)
        self.concrete_density = 2400  # kg/m³
        self.steel_yield_strength = 400  # MPa (SD400)
        self.concrete_strength = 24  # MPa (fck = 24 MPa)

        # Load factors (Korean Building Code)
        self.dead_load_factor = 1.2
        self.live_load_factor = 1.6

    def analyze_structure(
        self,
        spec: DesignSpec,
        building_use: str = "residential"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive structural analysis.

        Args:
            spec: Design specification
            building_use: Building use type (residential, office, retail, etc.)

        Returns:
            Dictionary with structural analysis results
        """
        results = {
            'building_info': self._get_building_info(spec),
            'load_analysis': self._calculate_loads(spec, building_use),
            'structural_grid': self._generate_structural_grid(spec),
            'column_design': self._design_columns(spec, building_use),
            'beam_design': self._design_beams(spec),
            'foundation': self._design_foundation(spec, building_use),
            'compliance': self._check_structural_compliance(spec)
        }

        return results

    def _get_building_info(self, spec: DesignSpec) -> Dict[str, Any]:
        """Get basic building information."""
        total_floors = len(spec.building.floors)
        building_height = sum(floor.height for floor in spec.building.floors)

        # Calculate total floor area
        total_area = 0.0
        for floor in spec.building.floors:
            for room in floor.rooms:
                area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )
                total_area += area

        return {
            'total_floors': total_floors,
            'building_height': building_height,
            'total_floor_area': total_area,
            'typical_floor_height': spec.building.floors[0].height if spec.building.floors else 0
        }

    def _calculate_loads(
        self,
        spec: DesignSpec,
        building_use: str
    ) -> Dict[str, Any]:
        """
        Calculate structural loads.

        Dead Load (고정하중):
        - Self-weight of structure
        - Weight of finishes, partitions, etc.

        Live Load (활하중):
        - Occupancy load
        - Movable equipment
        """
        # Live load per Korean Building Code (kN/m²)
        live_loads = {
            'residential': 2.0,  # 주거용
            'office': 2.5,       # 사무실
            'retail': 4.0,       # 상업용
            'storage': 5.0,      # 창고
            'parking': 2.5       # 주차장
        }

        live_load = live_loads.get(building_use, 2.0)

        # Dead load components (kN/m²)
        slab_thickness = 0.15  # 15cm slab
        slab_dead_load = slab_thickness * 24  # Concrete density ≈ 24 kN/m³

        finish_load = 1.0  # Finishes, ceiling, flooring
        partition_load = 1.0  # Movable partitions
        mep_load = 0.5  # MEP equipment

        total_dead_load = slab_dead_load + finish_load + partition_load + mep_load

        # Calculate total loads per floor
        loads_by_floor = []
        for floor in spec.building.floors:
            floor_area = 0.0
            for room in floor.rooms:
                area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )
                floor_area += area

            dead_load_total = total_dead_load * floor_area  # kN
            live_load_total = live_load * floor_area  # kN

            # Factored load (for LRFD design)
            factored_load = (self.dead_load_factor * dead_load_total +
                           self.live_load_factor * live_load_total)

            loads_by_floor.append({
                'floor_level': floor.level,
                'floor_area': floor_area,
                'dead_load_per_area': total_dead_load,
                'live_load_per_area': live_load,
                'total_dead_load': dead_load_total,
                'total_live_load': live_load_total,
                'factored_load': factored_load
            })

        return {
            'building_use': building_use,
            'live_load_intensity': live_load,
            'dead_load_intensity': total_dead_load,
            'loads_by_floor': loads_by_floor,
            'total_dead_load': sum(f['total_dead_load'] for f in loads_by_floor),
            'total_live_load': sum(f['total_live_load'] for f in loads_by_floor),
            'total_factored_load': sum(f['factored_load'] for f in loads_by_floor)
        }

    def _generate_structural_grid(self, spec: DesignSpec) -> Dict[str, Any]:
        """
        Generate structural grid (column layout).

        Typical column spacing: 6-8m for residential, 8-12m for commercial
        """
        # Analyze building footprint
        if not spec.building.floors or not spec.building.floors[0].rooms:
            return {'grid_lines': [], 'columns': []}

        # Get bounding box of first floor
        first_floor = spec.building.floors[0]
        all_coords = []
        for room in first_floor.rooms:
            all_coords.extend(room.geometry.coordinates[:-1])  # Exclude closing point

        if not all_coords:
            return {'grid_lines': [], 'columns': []}

        min_x = min(pt[0] for pt in all_coords)
        max_x = max(pt[0] for pt in all_coords)
        min_y = min(pt[1] for pt in all_coords)
        max_y = max(pt[1] for pt in all_coords)

        # Generate grid with 6m spacing
        grid_spacing = 6.0  # meters

        x_lines = []
        x = min_x
        while x <= max_x:
            x_lines.append(x)
            x += grid_spacing

        y_lines = []
        y = min_y
        while y <= max_y:
            y_lines.append(y)
            y += grid_spacing

        # Generate column positions at grid intersections
        columns = []
        for i, x in enumerate(x_lines):
            for j, y in enumerate(y_lines):
                columns.append({
                    'id': f"C-{i+1}{chr(65+j)}",  # C-1A, C-1B, etc.
                    'position': [x, y],
                    'grid_ref': f"{i+1}{chr(65+j)}"
                })

        return {
            'grid_spacing': grid_spacing,
            'x_grid_lines': x_lines,
            'y_grid_lines': y_lines,
            'column_count': len(columns),
            'columns': columns
        }

    def _design_columns(
        self,
        spec: DesignSpec,
        building_use: str
    ) -> Dict[str, Any]:
        """
        Design columns based on loads.

        Preliminary sizing for RC columns.
        """
        # Calculate loads
        load_data = self._calculate_loads(spec, building_use)
        grid_data = self._generate_structural_grid(spec)

        total_factored_load = load_data['total_factored_load']
        column_count = grid_data['column_count']

        if column_count == 0:
            return {'column_size': None, 'columns': []}

        # Load per column (simplified - assumes uniform distribution)
        load_per_column = total_factored_load / column_count  # kN

        # Column design
        # Axial capacity: P_n = 0.8 * [0.85 * f_ck * (A_g - A_st) + f_y * A_st]
        # Simplified: assume 1% steel ratio
        # P_n ≈ 0.8 * 0.85 * f_ck * A_g * 0.99 + 0.8 * f_y * A_g * 0.01

        fck = self.concrete_strength  # MPa
        fy = self.steel_yield_strength  # MPa

        # Required area
        # Solving: P_n >= Load
        # A_g >= Load / (0.8 * [0.85 * f_ck * 0.99 + f_y * 0.01])

        capacity_factor = 0.8 * (0.85 * fck * 0.99 + fy * 0.01 / 1000)  # Convert to MPa
        required_area = load_per_column / capacity_factor  # m²

        # Square column dimension
        column_size = math.sqrt(required_area) * 1000  # mm

        # Round up to nearest 50mm
        column_size = math.ceil(column_size / 50) * 50

        # Minimum column size: 300mm
        column_size = max(column_size, 300)

        return {
            'design_method': 'Simplified RC column design',
            'load_per_column': load_per_column,
            'required_area': required_area * 10000,  # cm²
            'column_size': f"{column_size}x{column_size}mm",
            'concrete_strength': fck,
            'steel_grade': f"SD{int(fy)}",
            'columns': grid_data['columns']
        }

    def _design_beams(self, spec: DesignSpec) -> Dict[str, Any]:
        """
        Design beams.

        Preliminary sizing for RC beams.
        """
        # Typical beam span: 6m
        span = 6.0  # meters
        floor_height = spec.building.floors[0].height if spec.building.floors else 3.0

        # Beam depth rule of thumb: span / 12 to span / 10
        beam_depth = span / 10  # meters
        beam_depth_mm = int(beam_depth * 1000)

        # Round to nearest 50mm
        beam_depth_mm = math.ceil(beam_depth_mm / 50) * 50

        # Beam width: typically 300-400mm for residential
        beam_width_mm = 300

        return {
            'typical_span': span,
            'beam_size': f"{beam_width_mm}x{beam_depth_mm}mm",
            'beam_width': beam_width_mm,
            'beam_depth': beam_depth_mm,
            'design_note': 'Preliminary sizing - detailed design required'
        }

    def _design_foundation(
        self,
        spec: DesignSpec,
        building_use: str
    ) -> Dict[str, Any]:
        """
        Preliminary foundation design.

        Assumes spread footings on competent soil.
        """
        # Soil bearing capacity (assumed)
        soil_bearing_capacity = 200  # kN/m² (typical for competent soil)

        # Calculate loads
        load_data = self._calculate_loads(spec, building_use)
        grid_data = self._generate_structural_grid(spec)

        total_load = load_data['total_dead_load'] + load_data['total_live_load']
        column_count = grid_data['column_count']

        if column_count == 0:
            return {'footing_size': None}

        load_per_column = total_load / column_count

        # Required footing area
        required_area = load_per_column / soil_bearing_capacity  # m²

        # Square footing dimension
        footing_size = math.sqrt(required_area)

        # Round up to nearest 0.1m
        footing_size = math.ceil(footing_size * 10) / 10

        # Minimum footing size: 1.5m
        footing_size = max(footing_size, 1.5)

        return {
            'foundation_type': 'Spread Footing',
            'soil_bearing_capacity': soil_bearing_capacity,
            'load_per_footing': load_per_column,
            'required_area': required_area,
            'footing_size': f"{footing_size}m x {footing_size}m",
            'footing_thickness': 0.5,  # meters (typical)
            'design_note': 'Assumes competent soil - geotechnical investigation required'
        }

    def _check_structural_compliance(self, spec: DesignSpec) -> Dict[str, Any]:
        """Check compliance with Korean Building Code."""
        building_height = sum(floor.height for floor in spec.building.floors)
        floor_count = len(spec.building.floors)

        # Korean Building Code checks
        checks = []

        # Height limit check (depends on zone)
        checks.append({
            'check': 'Building Height',
            'value': building_height,
            'requirement': 'Varies by zoning',
            'status': 'Review Required'
        })

        # Floor height check
        min_floor_height = 2.1  # meters (residential minimum)
        floor_heights_ok = all(
            floor.height >= min_floor_height
            for floor in spec.building.floors
        )

        checks.append({
            'check': 'Minimum Floor Height',
            'value': min(floor.height for floor in spec.building.floors) if spec.building.floors else 0,
            'requirement': f'>= {min_floor_height}m',
            'status': 'PASS' if floor_heights_ok else 'FAIL'
        })

        # Seismic design category (depends on location)
        checks.append({
            'check': 'Seismic Design',
            'value': 'Required for all buildings',
            'requirement': 'Korean Building Code',
            'status': 'Design Required'
        })

        all_pass = all(c['status'] == 'PASS' for c in checks if c['status'] in ['PASS', 'FAIL'])

        return {
            'checks': checks,
            'overall_status': 'PASS' if all_pass else 'REVIEW REQUIRED',
            'note': 'Detailed structural analysis required for construction'
        }

    def generate_report(
        self,
        analysis_results: Dict[str, Any],
        output_path: Path
    ):
        """
        Generate structural analysis report.

        Args:
            analysis_results: Results from analyze_structure()
            output_path: Path for output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get agent capabilities.

        Returns:
            Capabilities dictionary
        """
        return {
            'name': 'Structural Agent',
            'version': '1.0.0',
            'description': 'Structural design and analysis agent',
            'features': [
                'Load calculations (dead, live)',
                'Column and beam sizing',
                'Structural grid generation',
                'Foundation design (preliminary)',
                'Korean Building Code compliance',
                'RC (Reinforced Concrete) design'
            ],
            'design_codes': [
                'Korean Building Code (KBC)',
                'Korean Concrete Standard (KCS)'
            ],
            'note': 'Preliminary design only - detailed engineering required for construction'
        }
