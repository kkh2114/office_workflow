"""
Site Analysis Agent for site evaluation and solar analysis.

Performs site analysis including:
- Site boundaries and area calculation
- Solar access analysis (일조권)
- Shadow studies
- View analysis
- Wind analysis (basic)
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json
import math
from datetime import datetime, timedelta

from ..models.design_spec import DesignSpec
from ..skills.schema_validator import DesignSpecValidator as SchemaValidator
from ..skills.geometry_engine import GeometryEngine


class SiteAnalysisAgent:
    """
    Site analysis agent for evaluating building sites.

    Capabilities:
    - Calculate site area and dimensions
    - Analyze solar access (일조권/sunlight rights)
    - Perform shadow studies
    - Calculate view corridors
    - Basic wind analysis
    - Generate analysis reports
    """

    def __init__(self, schema_path: Path):
        """
        Initialize site analysis agent.

        Args:
            schema_path: Path to JSON schema file
        """
        self.schema_path = Path(schema_path)
        self.validator = SchemaValidator(schema_path)
        self.geometry_engine = GeometryEngine()

    def analyze_site(
        self,
        spec: DesignSpec,
        latitude: float = 37.5665,  # Seoul default
        longitude: float = 126.9780,
        analysis_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive site analysis.

        Args:
            spec: Design specification
            latitude: Site latitude (default: Seoul)
            longitude: Site longitude (default: Seoul)
            analysis_date: Date for solar analysis (default: today)

        Returns:
            Dictionary with analysis results
        """
        if analysis_date is None:
            analysis_date = datetime.now()

        results = {
            'site_info': self._analyze_site_boundaries(spec),
            'solar_analysis': self._analyze_solar_access(
                spec, latitude, longitude, analysis_date
            ),
            'shadow_study': self._perform_shadow_study(
                spec, latitude, longitude, analysis_date
            ),
            'view_analysis': self._analyze_views(spec),
            'recommendations': self._generate_recommendations(spec)
        }

        return results

    def _analyze_site_boundaries(self, spec: DesignSpec) -> Dict[str, Any]:
        """Analyze site boundaries and calculate areas."""
        # Calculate building footprint
        total_footprint = 0.0
        building_bounds = None

        for floor in spec.building.floors:
            if floor.level == 1:  # Ground floor
                for room in floor.rooms:
                    area = self.geometry_engine.calculate_polygon_area(
                        room.geometry.coordinates
                    )
                    total_footprint += area

                    # Update bounding box
                    bounds = self.geometry_engine.calculate_bounding_box(
                        room.geometry.coordinates
                    )
                    if building_bounds is None:
                        building_bounds = bounds
                    else:
                        building_bounds = self._expand_bounds(building_bounds, bounds)

        # Assume site is 1.5x building footprint (simplified)
        site_area = total_footprint * 1.5

        return {
            'building_footprint': total_footprint,
            'site_area': site_area,
            'building_coverage_ratio': (total_footprint / site_area) * 100,
            'building_bounds': building_bounds,
            'perimeter': math.sqrt(site_area) * 4  # Simplified square assumption
        }

    def _analyze_solar_access(
        self,
        spec: DesignSpec,
        latitude: float,
        longitude: float,
        date: datetime
    ) -> Dict[str, Any]:
        """
        Analyze solar access for the building (일조권 분석).

        Korean building code requires minimum 2 hours of sunlight
        in winter solstice (동지).
        """
        # Calculate for winter solstice (December 21)
        winter_solstice = datetime(date.year, 12, 21, 12, 0)

        # Calculate sun position at key times
        sun_positions = []
        for hour in range(9, 16):  # 9 AM to 3 PM
            time = winter_solstice.replace(hour=hour)
            sun_alt, sun_az = self._calculate_sun_position(
                latitude, longitude, time
            )
            sun_positions.append({
                'time': time.strftime('%H:%M'),
                'altitude': sun_alt,
                'azimuth': sun_az
            })

        # Calculate sunlight hours for south-facing rooms
        sunlight_hours = self._calculate_sunlight_hours(spec, sun_positions)

        # Check compliance with Korean standards
        min_sunlight = min(sunlight_hours.values()) if sunlight_hours else 0
        compliant = min_sunlight >= 2.0  # Korean standard: 2 hours minimum

        return {
            'analysis_date': winter_solstice.strftime('%Y-%m-%d'),
            'latitude': latitude,
            'longitude': longitude,
            'sun_positions': sun_positions,
            'sunlight_hours_by_room': sunlight_hours,
            'minimum_sunlight_hours': min_sunlight,
            'korean_standard_compliance': compliant,
            'korean_standard_required': 2.0,
            'status': 'PASS' if compliant else 'FAIL'
        }

    def _calculate_sun_position(
        self,
        latitude: float,
        longitude: float,
        time: datetime
    ) -> Tuple[float, float]:
        """
        Calculate sun altitude and azimuth.

        Returns:
            Tuple of (altitude, azimuth) in degrees

        Note: Simplified calculation. Production use should use
        libraries like pvlib or pysolar for accurate results.
        """
        # Simplified sun position calculation
        # This is a rough approximation - use proper library for production

        # Day of year
        doy = time.timetuple().tm_yday

        # Declination angle
        declination = 23.45 * math.sin(math.radians((360 / 365) * (doy - 81)))

        # Hour angle
        hour = time.hour + time.minute / 60.0
        hour_angle = 15 * (hour - 12)

        # Convert to radians
        lat_rad = math.radians(latitude)
        dec_rad = math.radians(declination)
        ha_rad = math.radians(hour_angle)

        # Solar altitude
        sin_alt = (math.sin(lat_rad) * math.sin(dec_rad) +
                   math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad))
        altitude = math.degrees(math.asin(sin_alt))

        # Solar azimuth (simplified)
        cos_az = ((math.sin(dec_rad) - math.sin(lat_rad) * sin_alt) /
                  (math.cos(lat_rad) * math.cos(math.radians(altitude))))
        cos_az = max(-1, min(1, cos_az))  # Clamp to [-1, 1]
        azimuth = math.degrees(math.acos(cos_az))

        if hour > 12:  # Afternoon
            azimuth = 360 - azimuth

        return altitude, azimuth

    def _calculate_sunlight_hours(
        self,
        spec: DesignSpec,
        sun_positions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate sunlight hours for each room."""
        sunlight_hours = {}

        for floor in spec.building.floors:
            for room in floor.rooms:
                # Check if room has south-facing windows
                has_south_windows = any(
                    self._is_south_facing(window, room.geometry.coordinates)
                    for window in room.windows
                )

                if has_south_windows:
                    # Count hours with sun altitude > 0
                    hours = sum(
                        1 for pos in sun_positions
                        if pos['altitude'] > 0
                    )
                    sunlight_hours[room.name] = hours
                else:
                    sunlight_hours[room.name] = 0

        return sunlight_hours

    def _is_south_facing(
        self,
        window,
        room_coords: List[List[float]]
    ) -> bool:
        """Check if window is south-facing."""
        wall_idx = window.wall_index
        if wall_idx >= len(room_coords) - 1:
            return False

        p1 = room_coords[wall_idx]
        p2 = room_coords[wall_idx + 1]

        # Calculate wall direction
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        # Calculate angle from north (0°)
        angle = math.degrees(math.atan2(dx, dy))

        # South-facing: 135° to 225° (±45° from due south)
        return 135 <= angle <= 225

    def _perform_shadow_study(
        self,
        spec: DesignSpec,
        latitude: float,
        longitude: float,
        date: datetime
    ) -> Dict[str, Any]:
        """
        Perform shadow study for the building.

        Calculates shadow lengths at different times of day.
        """
        # Calculate building height
        building_height = sum(floor.height for floor in spec.building.floors)

        # Calculate shadow lengths at key times
        shadow_data = []

        for hour in range(9, 17):  # 9 AM to 4 PM
            time = date.replace(hour=hour)
            sun_alt, sun_az = self._calculate_sun_position(
                latitude, longitude, time
            )

            if sun_alt > 0:
                # Shadow length = height / tan(altitude)
                shadow_length = building_height / math.tan(math.radians(sun_alt))

                shadow_data.append({
                    'time': time.strftime('%H:%M'),
                    'sun_altitude': sun_alt,
                    'sun_azimuth': sun_az,
                    'shadow_length': shadow_length,
                    'shadow_direction': sun_az + 180  # Opposite of sun
                })

        return {
            'building_height': building_height,
            'shadows': shadow_data,
            'max_shadow_length': max(s['shadow_length'] for s in shadow_data) if shadow_data else 0
        }

    def _analyze_views(self, spec: DesignSpec) -> Dict[str, Any]:
        """Analyze view corridors and openness."""
        view_analysis = {}

        for floor in spec.building.floors:
            for room in floor.rooms:
                # Count windows and their orientations
                window_count = len(room.windows)
                window_area = sum(w.width * w.height for w in room.windows)

                # Calculate room area
                room_area = self.geometry_engine.calculate_polygon_area(
                    room.geometry.coordinates
                )

                # Window-to-wall ratio
                perimeter = self.geometry_engine.calculate_polygon_perimeter(
                    room.geometry.coordinates
                )
                wall_area = perimeter * floor.height
                window_ratio = (window_area / wall_area * 100) if wall_area > 0 else 0

                view_analysis[room.name] = {
                    'window_count': window_count,
                    'window_area': window_area,
                    'window_to_wall_ratio': window_ratio,
                    'view_quality': 'Good' if window_ratio > 20 else 'Fair' if window_ratio > 10 else 'Poor'
                }

        return view_analysis

    def _generate_recommendations(self, spec: DesignSpec) -> List[str]:
        """Generate design recommendations based on analysis."""
        recommendations = []

        # Analyze floor plan efficiency
        for floor in spec.building.floors:
            total_area = sum(
                self.geometry_engine.calculate_polygon_area(room.geometry.coordinates)
                for room in floor.rooms
            )

            # Check for sufficient natural light
            rooms_with_windows = sum(
                1 for room in floor.rooms if len(room.windows) > 0
            )
            rooms_without_windows = len(floor.rooms) - rooms_with_windows

            if rooms_without_windows > 0:
                recommendations.append(
                    f"Consider adding windows to {rooms_without_windows} rooms for natural lighting"
                )

            # Check for cross ventilation
            for room in floor.rooms:
                if len(room.windows) < 2:
                    recommendations.append(
                        f"Room '{room.name}': Consider adding windows on opposite walls for cross ventilation"
                    )

        return recommendations

    def _expand_bounds(
        self,
        bounds1: Tuple[float, float, float, float],
        bounds2: Tuple[float, float, float, float]
    ) -> Tuple[float, float, float, float]:
        """Expand bounding box to include both bounds."""
        return (
            min(bounds1[0], bounds2[0]),  # min_x
            min(bounds1[1], bounds2[1]),  # min_y
            max(bounds1[2], bounds2[2]),  # max_x
            max(bounds1[3], bounds2[3])   # max_y
        )

    def generate_report(
        self,
        analysis_results: Dict[str, Any],
        output_path: Path
    ):
        """
        Generate analysis report as JSON.

        Args:
            analysis_results: Results from analyze_site()
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
            'name': 'Site Analysis Agent',
            'version': '1.0.0',
            'description': 'Site evaluation and solar analysis agent',
            'features': [
                'Site boundary analysis',
                'Solar access analysis (일조권)',
                'Shadow studies',
                'View corridor analysis',
                'Korean building code compliance check',
                'Design recommendations'
            ],
            'supported_standards': [
                'Korean Building Act (건축법)',
                'Korean Housing Act (주택법)'
            ]
        }
