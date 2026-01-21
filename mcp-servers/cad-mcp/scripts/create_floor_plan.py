#!/usr/bin/env python3
"""
Create Floor Plan Script

Called by MCP server to generate DXF floor plans from JSON specs.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.autocad_agent import AutoCADAgent


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: create_floor_plan.py <json_path> <output_path> [floor_level]", file=sys.stderr)
        sys.exit(1)

    json_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    floor_level = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    # Validate inputs
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    # Initialize agent
    schema_path = project_root / "config" / "schemas" / "design_spec.schema.json"
    agent = AutoCADAgent(schema_path=schema_path)

    try:
        # Generate floor plan
        print(f"Generating floor plan from {json_path}...")
        agent.create_floor_plan_from_json(
            json_path=json_path,
            output_path=output_path,
            floor_level=floor_level
        )

        print(f"✓ Floor plan generated: {output_path}")

        # Analyze result
        analysis = agent.analyze_floor_plan_from_json(json_path, floor_level)
        print("\nFloor Plan Analysis:")
        print(f"  Total Rooms: {analysis['total_rooms']}")
        print(f"  Total Area: {analysis['total_area']:.2f} m²")
        print(f"  Rooms:")
        for room in analysis['rooms']:
            print(f"    - {room['name']}: {room['area']:.2f} m²")

        sys.exit(0)

    except Exception as e:
        print(f"Error generating floor plan: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
