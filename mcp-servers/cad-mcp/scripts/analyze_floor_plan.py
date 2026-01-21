#!/usr/bin/env python3
"""
Analyze Floor Plan Script

Called by MCP server to analyze floor plans from DesignSpec JSON.
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
    if len(sys.argv) < 2:
        print("Usage: analyze_floor_plan.py <json_path> [floor_level]", file=sys.stderr)
        sys.exit(1)

    json_path = Path(sys.argv[1])
    floor_level = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    # Validate inputs
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    # Initialize agent
    schema_path = project_root / "config" / "schemas" / "design_spec.schema.json"
    agent = AutoCADAgent(schema_path=schema_path)

    try:
        # Analyze floor plan
        print(f"Analyzing floor plan from {json_path}...")
        analysis = agent.analyze_floor_plan_from_json(json_path, floor_level)

        # Print analysis in formatted JSON
        print("\n" + "=" * 60)
        print("FLOOR PLAN ANALYSIS")
        print("=" * 60)
        print(json.dumps(analysis, indent=2, ensure_ascii=False))

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total Rooms: {analysis['total_rooms']}")
        print(f"Total Area: {analysis['total_area']:.2f} m²")
        print(f"Total Perimeter: {analysis['total_perimeter']:.2f} m")
        print(f"Total Doors: {analysis['total_doors']}")
        print(f"Total Windows: {analysis['total_windows']}")
        print(f"Total Furniture: {analysis['total_furniture']}")

        print("\nRooms:")
        for room in analysis['rooms']:
            print(f"  - {room['name']} ({room['type']})")
            print(f"    Area: {room['area']:.2f} m²")
            print(f"    Perimeter: {room['perimeter']:.2f} m")
            print(f"    Doors: {room['door_count']}, Windows: {room['window_count']}")

        sys.exit(0)

    except Exception as e:
        print(f"Error analyzing floor plan: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
