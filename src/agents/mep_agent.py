"""
MEP Agent for Mechanical, Electrical, and Plumbing system design.

Performs MEP analysis including:
- HVAC system sizing and layout
- Electrical load calculations and distribution
- Plumbing fixture requirements
- Fire protection systems
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import math

from ..models.design_spec import DesignSpec, Room, RoomType
from ..skills.schema_validator import DesignSpecValidator as SchemaValidator
from ..skills.geometry_engine import GeometryEngine


class MEPAgent:
    """
    MEP (Mechanical, Electrical, Plumbing) design agent.

    Capabilities:
    - HVAC system design
    - Electrical load calculation
    - Lighting design
    - Plumbing fixture layout
    - Fire protection system
    - Energy efficiency analysis
    """

    def __init__(self, schema_path: Path):
        """
        Initialize MEP agent.

        Args:
            schema_path: Path to JSON schema file
        """
        self.schema_path = Path(schema_path)
        self.validator = SchemaValidator(schema_path)
        self.geometry_engine = GeometryEngine()

    def analyze_mep_systems(
        self,
        spec: DesignSpec,
        building_use: str = "residential",
        climate_zone: str = "temperate"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive MEP analysis.

        Args:
            spec: Design specification
            building_use: Building use type
            climate_zone: Climate zone for HVAC sizing

        Returns:
            Dictionary with MEP analysis results
        """
        results = {
            'hvac': self._design_hvac(spec, climate_zone),
            'electrical': self._design_electrical(spec, building_use),
            'plumbing': self._design_plumbing(spec),
            'fire_protection': self._design_fire_protection(spec),
            'energy_analysis': self._analyze_energy(spec, climate_zone)
        }

        return results

    def _design_hvac(
        self,
        spec: DesignSpec,
        climate_zone: str
    ) -> Dict[str, Any]:
        """
        Design HVAC (Heating, Ventilation, Air Conditioning) system.

        Korean residential standard:
        - Cooling capacity: ~150-180 W/m² (depends on insulation)
        - Heating capacity: ~100-120 W/m² (with floor heating)
        - Ventilation: 0.5-1.0 air changes per hour (ACH)
        """
        # Cooling/heating loads (W/m²)
        load_factors = {
            'temperate': {'cooling': 150, 'heating': 100},
            'hot': {'cooling': 180, 'heating': 80},
            'cold': {'cooling': 120, 'heating': 140}
        }

        factors = load_factors.get(climate_zone, load_factors['temperate'])

        hvac_by_room = []
        total_cooling_load = 0.0
        total_heating_load = 0.0

        for floor in spec.building.floors:
            for room in floor.rooms:
                # Calculate room area
                area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )
                volume = area * floor.height

                # Calculate loads
                cooling_load = area * factors['cooling']  # Watts
                heating_load = area * factors['heating']  # Watts

                # Air changes per hour (ACH)
                ach = 0.7  # Standard for residential
                ventilation_rate = volume * ach / 3600  # m³/s

                # Recommended AC capacity (BTU/hr)
                # 1 Watt ≈ 3.412 BTU/hr
                ac_capacity_btu = cooling_load * 3.412

                hvac_by_room.append({
                    'room_name': room.name,
                    'room_type': room.type.value,
                    'area': area,
                    'volume': volume,
                    'cooling_load': cooling_load,  # W
                    'heating_load': heating_load,  # W
                    'ac_capacity_btu': ac_capacity_btu,
                    'ventilation_rate': ventilation_rate,  # m³/s
                    'recommended_ac': self._recommend_ac_size(ac_capacity_btu)
                })

                total_cooling_load += cooling_load
                total_heating_load += heating_load

        return {
            'climate_zone': climate_zone,
            'total_cooling_load': total_cooling_load / 1000,  # kW
            'total_heating_load': total_heating_load / 1000,  # kW
            'hvac_by_room': hvac_by_room,
            'system_recommendations': self._recommend_hvac_system(spec, total_cooling_load)
        }

    def _recommend_ac_size(self, btu_hr: float) -> str:
        """Recommend AC size based on BTU/hr."""
        btu_ranges = [
            (9000, "9,000 BTU (2.6kW)"),
            (12000, "12,000 BTU (3.5kW)"),
            (18000, "18,000 BTU (5.3kW)"),
            (24000, "24,000 BTU (7.0kW)"),
            (float('inf'), "30,000+ BTU (8.8kW+)")
        ]

        for threshold, size in btu_ranges:
            if btu_hr <= threshold:
                return size

        return "Custom sizing required"

    def _recommend_hvac_system(
        self,
        spec: DesignSpec,
        total_cooling_load: float
    ) -> str:
        """Recommend HVAC system type."""
        total_area = sum(
            self.geometry_engine.calculate_polygon_area(room.geometry.coordinates)
            for floor in spec.building.floors
            for room in floor.rooms
        )

        if total_area < 100:
            return "Split AC units + Electric floor heating"
        elif total_area < 200:
            return "Multi-split AC system + Hydronic floor heating"
        else:
            return "Central HVAC system with VRF (Variable Refrigerant Flow)"

    def _design_electrical(
        self,
        spec: DesignSpec,
        building_use: str
    ) -> Dict[str, Any]:
        """
        Design electrical system.

        Korean residential standard:
        - General power: 40-60 VA/m²
        - Lighting: 10-15 VA/m²
        - HVAC: 100-150 VA/m²
        - Receptacles: 2-3 outlets per room
        """
        # Load densities (VA/m²)
        load_densities = {
            'residential': {'general': 50, 'lighting': 12, 'hvac': 120},
            'office': {'general': 80, 'lighting': 15, 'hvac': 150},
            'retail': {'general': 100, 'lighting': 20, 'hvac': 180}
        }

        densities = load_densities.get(building_use, load_densities['residential'])

        electrical_by_room = []
        total_load = 0.0

        for floor in spec.building.floors:
            for room in floor.rooms:
                area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )

                # Calculate loads
                general_load = area * densities['general']
                lighting_load = area * densities['lighting']
                hvac_load = area * densities['hvac']
                room_total = general_load + lighting_load + hvac_load

                # Lighting fixtures
                lux_requirement = self._get_lighting_requirement(room.type)
                fixture_count = self._calculate_lighting_fixtures(area, lux_requirement)

                # Outlets
                outlet_count = self._calculate_outlet_count(room.type, area)

                electrical_by_room.append({
                    'room_name': room.name,
                    'room_type': room.type.value,
                    'area': area,
                    'general_load': general_load,
                    'lighting_load': lighting_load,
                    'hvac_load': hvac_load,
                    'total_load': room_total,
                    'lighting_fixtures': fixture_count,
                    'outlets': outlet_count,
                    'required_illuminance': lux_requirement
                })

                total_load += room_total

        # Main panel sizing
        # Apply demand factor (0.6-0.7 for residential)
        demand_factor = 0.65
        design_load = total_load * demand_factor

        # Calculate required amperage (assuming 220V single phase)
        voltage = 220
        amperage = design_load / voltage

        # Select panel size (round up to standard sizes)
        panel_sizes = [60, 100, 150, 200, 400]
        panel_size = next((size for size in panel_sizes if size >= amperage), 400)

        return {
            'total_connected_load': total_load / 1000,  # kVA
            'design_load': design_load / 1000,  # kVA
            'demand_factor': demand_factor,
            'required_amperage': amperage,
            'recommended_panel': f"{panel_size}A",
            'voltage': f"{voltage}V Single Phase",
            'electrical_by_room': electrical_by_room
        }

    def _get_lighting_requirement(self, room_type: RoomType) -> int:
        """Get required illuminance (lux) for room type."""
        requirements = {
            RoomType.LIVING_ROOM: 150,
            RoomType.BEDROOM: 100,
            RoomType.KITCHEN: 300,
            RoomType.BATHROOM: 200,
            RoomType.DINING_ROOM: 150,
            RoomType.STUDY: 300,
            RoomType.HALLWAY: 100,
            RoomType.ENTRANCE: 150,
        }
        return requirements.get(room_type, 150)

    def _calculate_lighting_fixtures(self, area: float, lux_requirement: int) -> int:
        """Calculate number of lighting fixtures needed."""
        # Assuming LED fixtures: 1000 lumens per fixture, 50% efficiency
        lumens_per_fixture = 1000
        efficiency = 0.5

        # Required lumens = lux × area
        required_lumens = lux_requirement * area

        # Number of fixtures
        fixture_count = math.ceil(required_lumens / (lumens_per_fixture * efficiency))

        return max(fixture_count, 1)

    def _calculate_outlet_count(self, room_type: RoomType, area: float) -> int:
        """Calculate number of electrical outlets needed."""
        base_outlets = {
            RoomType.LIVING_ROOM: 6,
            RoomType.BEDROOM: 4,
            RoomType.KITCHEN: 6,
            RoomType.BATHROOM: 2,
            RoomType.DINING_ROOM: 2,
            RoomType.STUDY: 4,
            RoomType.HALLWAY: 1,
            RoomType.ENTRANCE: 1,
        }

        base = base_outlets.get(room_type, 2)

        # Add 1 outlet per 10m² beyond base
        additional = int(area / 10)

        return base + additional

    def _design_plumbing(self, spec: DesignSpec) -> Dict[str, Any]:
        """
        Design plumbing system.

        Includes water supply and drainage.
        """
        plumbing_by_room = []
        total_fixtures = 0

        # Fixture units (for pipe sizing)
        fixture_units = 0.0

        for floor in spec.building.floors:
            for room in floor.rooms:
                fixtures = self._get_plumbing_fixtures(room.type)

                if fixtures:
                    area = self.geometry_engine.calculate_polygon_area(
                        room.geometry.coordinates
                    )

                    room_fu = sum(f['fixture_units'] for f in fixtures)
                    fixture_units += room_fu

                    plumbing_by_room.append({
                        'room_name': room.name,
                        'room_type': room.type.value,
                        'fixtures': fixtures,
                        'fixture_count': len(fixtures),
                        'fixture_units': room_fu
                    })

                    total_fixtures += len(fixtures)

        # Water supply pipe sizing (simplified)
        # Korean standard: 20mm for < 10 FU, 25mm for < 30 FU, 32mm for < 60 FU
        if fixture_units < 10:
            supply_pipe = "20mm (3/4\")"
        elif fixture_units < 30:
            supply_pipe = "25mm (1\")"
        elif fixture_units < 60:
            supply_pipe = "32mm (1-1/4\")"
        else:
            supply_pipe = "40mm (1-1/2\") or larger"

        # Drainage pipe
        drainage_pipe = "100mm (4\") main drain"

        return {
            'total_fixtures': total_fixtures,
            'total_fixture_units': fixture_units,
            'supply_pipe_size': supply_pipe,
            'drainage_pipe_size': drainage_pipe,
            'plumbing_by_room': plumbing_by_room,
            'hot_water_system': 'Central boiler or tankless water heater'
        }

    def _get_plumbing_fixtures(self, room_type: RoomType) -> List[Dict[str, Any]]:
        """Get plumbing fixtures for room type."""
        fixtures_by_type = {
            RoomType.BATHROOM: [
                {'name': 'Sink', 'fixture_units': 1.0},
                {'name': 'Toilet', 'fixture_units': 3.0},
                {'name': 'Shower/Bathtub', 'fixture_units': 2.0}
            ],
            RoomType.KITCHEN: [
                {'name': 'Kitchen Sink', 'fixture_units': 1.5},
                {'name': 'Dishwasher', 'fixture_units': 1.5}
            ],
            RoomType.UTILITY: [
                {'name': 'Washing Machine', 'fixture_units': 2.0},
                {'name': 'Utility Sink', 'fixture_units': 1.0}
            ]
        }

        return fixtures_by_type.get(room_type, [])

    def _design_fire_protection(self, spec: DesignSpec) -> Dict[str, Any]:
        """
        Design fire protection system.

        Korean building code requirements.
        """
        building_height = sum(floor.height for floor in spec.building.floors)
        floor_count = len(spec.building.floors)

        # Fire protection requirements
        requirements = []

        # Fire extinguishers (required for all buildings)
        requirements.append({
            'system': 'Fire Extinguishers',
            'required': True,
            'specification': 'ABC type, 3.3kg minimum, every 20m travel distance'
        })

        # Smoke detectors (required for residential)
        requirements.append({
            'system': 'Smoke Detectors',
            'required': True,
            'specification': 'Photoelectric type, one per room and hallway'
        })

        # Sprinkler system (required for buildings > 6 floors or > 1000m²)
        total_area = sum(
            self.geometry_engine.calculate_polygon_area(room.geometry.coordinates)
            for floor in spec.building.floors
            for room in floor.rooms
        )

        if floor_count > 6 or total_area > 1000:
            requirements.append({
                'system': 'Sprinkler System',
                'required': True,
                'specification': 'Wet pipe system, NFPA 13 or Korean KS standards'
            })

        # Fire alarm (required for buildings > 3 floors)
        if floor_count > 3:
            requirements.append({
                'system': 'Fire Alarm System',
                'required': True,
                'specification': 'Addressable system with voice evacuation'
            })

        # Emergency lighting (required for multi-story)
        if floor_count > 2:
            requirements.append({
                'system': 'Emergency Lighting',
                'required': True,
                'specification': '90-minute backup, exit signs in Korean/English'
            })

        return {
            'building_height': building_height,
            'floor_count': floor_count,
            'total_area': total_area,
            'requirements': requirements,
            'code_reference': 'Korean Building Act Article 49 (소방시설)'
        }

    def _analyze_energy(
        self,
        spec: DesignSpec,
        climate_zone: str
    ) -> Dict[str, Any]:
        """
        Analyze energy consumption and efficiency.

        Korean building energy rating system.
        """
        total_area = sum(
            self.geometry_engine.calculate_polygon_area(room.geometry.coordinates)
            for floor in spec.building.floors
            for room in floor.rooms
        )

        # Estimated annual energy consumption (kWh/m²/year)
        # Korean residential average: 120-180 kWh/m²/year
        energy_intensity = 150  # kWh/m²/year (mid-range)

        annual_consumption = total_area * energy_intensity

        # Breakdown by system
        hvac_ratio = 0.50  # 50% for HVAC
        lighting_ratio = 0.15  # 15% for lighting
        hot_water_ratio = 0.20  # 20% for hot water
        appliances_ratio = 0.15  # 15% for appliances

        return {
            'total_area': total_area,
            'energy_intensity': energy_intensity,
            'annual_consumption': annual_consumption,  # kWh/year
            'consumption_breakdown': {
                'hvac': annual_consumption * hvac_ratio,
                'lighting': annual_consumption * lighting_ratio,
                'hot_water': annual_consumption * hot_water_ratio,
                'appliances': annual_consumption * appliances_ratio
            },
            'estimated_annual_cost': annual_consumption * 0.12,  # KRW/kWh ≈ 120 won
            'recommendations': [
                'Install LED lighting for 30% energy savings',
                'Use high-efficiency HVAC (SEER > 13)',
                'Add wall/roof insulation to reduce HVAC load',
                'Install solar panels for renewable energy'
            ]
        }

    def generate_report(
        self,
        analysis_results: Dict[str, Any],
        output_path: Path
    ):
        """
        Generate MEP analysis report.

        Args:
            analysis_results: Results from analyze_mep_systems()
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
            'name': 'MEP Agent',
            'version': '1.0.0',
            'description': 'MEP systems design agent',
            'features': [
                'HVAC system sizing',
                'Electrical load calculation',
                'Lighting design',
                'Plumbing fixture layout',
                'Fire protection systems',
                'Energy efficiency analysis'
            ],
            'systems': ['Mechanical', 'Electrical', 'Plumbing', 'Fire Protection'],
            'standards': [
                'Korean Building Code',
                'Korean Electrical Safety Code',
                'Korean Fire Safety Standards'
            ]
        }
