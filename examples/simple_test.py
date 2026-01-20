#!/usr/bin/env python3
"""
Simple test script for LLM-CAD Integration System.
Generates a 3LDK apartment floor plan from JSON specification.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import AutoCADAgent
from src.models import DesignSpec
import json


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main test function."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("LLM-CAD Integration System - Simple Test")
    logger.info("=" * 60)

    # Paths
    project_root = Path(__file__).parent.parent
    spec_path = project_root / "tests" / "fixtures" / "3ldk_apartment.json"
    schema_path = project_root / "config" / "schemas" / "design_spec.schema.json"
    output_path = project_root / "output" / "3ldk_apartment.dxf"

    # Check if spec file exists
    if not spec_path.exists():
        logger.error(f"Specification file not found: {spec_path}")
        return 1

    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        return 1

    # Load specification
    logger.info(f"Loading specification from: {spec_path}")
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec_dict = json.load(f)

    spec = DesignSpec(**spec_dict)
    logger.info(f"Project: {spec.project_info.name}")
    logger.info(f"Client: {spec.project_info.client}")

    # Create agent
    logger.info("Initializing AutoCAD Agent...")
    agent = AutoCADAgent(
        wall_thickness=0.2,
        schema_path=schema_path
    )

    # Analyze floor plan
    logger.info("Analyzing floor plan...")
    stats = agent.analyze_floor_plan(spec, floor_level=1)

    logger.info(f"\nFloor Plan Statistics:")
    logger.info(f"  Total Area: {stats['total_area']} ㎡")
    logger.info(f"  Number of Rooms: {stats['num_rooms']}")
    logger.info(f"\n  Room Details:")

    for room in stats['rooms']:
        logger.info(f"    - {room['name']}: {room['area']} ㎡")
        logger.info(f"      Doors: {room['num_doors']}, "
                   f"Windows: {room['num_windows']}, "
                   f"Furniture: {room['num_furniture']}")

    # Generate floor plan
    logger.info(f"\nGenerating DXF file...")
    logger.info(f"Output path: {output_path}")

    try:
        result_path = agent.create_floor_plan(
            spec=spec,
            output_path=output_path,
            floor_level=1,
            validate=True
        )

        logger.info("=" * 60)
        logger.info("SUCCESS!")
        logger.info(f"Floor plan generated: {result_path}")
        logger.info(f"File size: {result_path.stat().st_size:,} bytes")
        logger.info("=" * 60)
        logger.info("\nYou can now open the DXF file in:")
        logger.info("  - AutoCAD")
        logger.info("  - BricsCAD")
        logger.info("  - LibreCAD")
        logger.info("  - FreeCAD")
        logger.info("  - Any DXF viewer")

        return 0

    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
