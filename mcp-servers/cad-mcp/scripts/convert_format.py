#!/usr/bin/env python3
"""
Convert Spec Format Script

Called by MCP server to convert DesignSpec between formats.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def convert_format(input_path: Path, output_path: Path, target_format: str):
    """
    Convert spec between formats.

    Args:
        input_path: Input file path
        output_path: Output file path
        target_format: Target format (json, yaml, json-pretty, json-minified)
    """
    # Read input
    with open(input_path, 'r', encoding='utf-8') as f:
        if input_path.suffix == '.json':
            data = json.load(f)
        elif input_path.suffix in ['.yaml', '.yml']:
            try:
                import yaml
                data = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML not installed. Run: pip install pyyaml")
        else:
            raise ValueError(f"Unsupported input format: {input_path.suffix}")

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if target_format == 'json-pretty':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    elif target_format == 'json-minified':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
    elif target_format == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    elif target_format == 'yaml':
        try:
            import yaml
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        except ImportError:
            raise ImportError("PyYAML not installed. Run: pip install pyyaml")
    else:
        raise ValueError(f"Unsupported target format: {target_format}")


def main():
    """Main entry point."""
    if len(sys.argv) < 4:
        print("Usage: convert_format.py <input_path> <output_path> <format>", file=sys.stderr)
        print("Formats: json, yaml, json-pretty, json-minified", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    target_format = sys.argv[3]

    # Validate inputs
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        print(f"Converting {input_path} to {target_format}...")
        convert_format(input_path, output_path, target_format)

        print(f"✓ Conversion successful!")
        print(f"  Output: {output_path}")

        # Show file sizes
        input_size = input_path.stat().st_size
        output_size = output_path.stat().st_size
        print(f"  Input size: {input_size} bytes")
        print(f"  Output size: {output_size} bytes")

        sys.exit(0)

    except Exception as e:
        print(f"Error converting format: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
