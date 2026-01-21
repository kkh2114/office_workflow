#!/usr/bin/env python3
"""
Validate Design Spec Script

Called by MCP server to validate DesignSpec JSON files.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.skills.schema_validator import SchemaValidator


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_spec.py <json_path>", file=sys.stderr)
        sys.exit(1)

    json_path = Path(sys.argv[1])

    # Validate inputs
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    # Initialize validator
    schema_path = project_root / "config" / "schemas" / "design_spec.schema.json"
    validator = SchemaValidator(schema_path=schema_path)

    try:
        # Load JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            spec_data = json.load(f)

        print(f"Validating {json_path}...")

        # Validate against schema
        result = validator.validate_json(spec_data)

        if result['valid']:
            print("✓ Schema validation: PASSED")
        else:
            print("✗ Schema validation: FAILED")
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")
            sys.exit(1)

        # Validate with Pydantic model
        result = validator.validate_model(spec_data)

        if result['valid']:
            print("✓ Model validation: PASSED")
        else:
            print("✗ Model validation: FAILED")
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")
            sys.exit(1)

        # Validate geometry
        result = validator.validate_geometry(spec_data)

        if result['valid']:
            print("✓ Geometry validation: PASSED")
        else:
            print("✗ Geometry validation: FAILED")
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")
            sys.exit(1)

        print("\n✓ All validations passed!")
        sys.exit(0)

    except Exception as e:
        print(f"Error validating spec: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
