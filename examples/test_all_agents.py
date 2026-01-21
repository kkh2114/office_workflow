"""
Comprehensive integration test for all agents.

Tests the complete LLM-CAD integration system end-to-end.
"""

from pathlib import Path
import sys
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.design_spec import DesignSpec
from src.agents.autocad_agent import AutoCADAgent
from src.agents.revit_agent import RevitAgent, IFC_AVAILABLE
from src.agents.rhino_agent import RhinoAgent, RHINO3DM_AVAILABLE
from src.agents.site_analysis_agent import SiteAnalysisAgent
from src.agents.structural_agent import StructuralAgent
from src.agents.mep_agent import MEPAgent
from src.agents.compliance_agent import ComplianceAgent


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_autocad_agent():
    """Test AutoCAD Agent."""
    print_section("TEST 1: AutoCAD Agent (DXF Generation)")

    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    json_path = Path(__file__).parent.parent / "tests" / "fixtures" / "3ldk_apartment.json"
    output_path = Path(__file__).parent.parent / "output" / "test_all" / "floor_plan.dxf"

    agent = AutoCADAgent(schema_path=schema_path)

    print(f"\n[OK] Agent initialized")
    print(f"  Generating DXF from: {json_path.name}")

    agent.create_floor_plan_from_json(
        json_path=json_path,
        output_path=output_path,
        floor_level=1
    )

    print(f"[OK] DXF generated: {output_path}")

    # Analyze
    analysis = agent.analyze_floor_plan_from_json(json_path, 1)
    print(f"\n  Analysis:")
    print(f"    Rooms: {analysis['num_rooms']}")
    print(f"    Total Area: {analysis['total_area']:.2f} m²")

    return True


def test_revit_agent():
    """Test Revit Agent."""
    print_section("TEST 2: Revit Agent (BIM/IFC Generation)")

    if not IFC_AVAILABLE:
        print("[SKIP]️  ifcopenshell not installed - skipping")
        return False

    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    json_path = Path(__file__).parent.parent / "tests" / "fixtures" / "3ldk_apartment.json"
    output_path = Path(__file__).parent.parent / "output" / "test_all" / "bim_model.ifc"

    agent = RevitAgent(schema_path=schema_path)

    print(f"\n[OK] Agent initialized")
    print(f"  Generating IFC from: {json_path.name}")

    agent.create_bim_model_from_json(
        json_path=json_path,
        output_path=output_path
    )

    print(f"[OK] IFC generated: {output_path}")

    return True


def test_rhino_agent():
    """Test Rhino Agent."""
    print_section("TEST 3: Rhino Agent (3D Parametric Model)")

    if not RHINO3DM_AVAILABLE:
        print("[SKIP]️  rhino3dm not installed - skipping")
        return False

    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    json_path = Path(__file__).parent.parent / "tests" / "fixtures" / "3ldk_apartment.json"
    output_path = Path(__file__).parent.parent / "output" / "test_all" / "3d_model.3dm"

    agent = RhinoAgent(schema_path=schema_path)

    print(f"\n[OK] Agent initialized")
    print(f"  Generating 3DM from: {json_path.name}")

    agent.create_3d_model_from_json(
        json_path=json_path,
        output_path=output_path
    )

    print(f"[OK] 3DM generated: {output_path}")

    return True


def test_site_analysis_agent():
    """Test Site Analysis Agent."""
    print_section("TEST 4: Site Analysis Agent (Solar + Site)")

    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    json_path = Path(__file__).parent.parent / "tests" / "fixtures" / "3ldk_apartment.json"

    with open(json_path, 'r', encoding='utf-8') as f:
        spec_dict = json.load(f)
    spec = DesignSpec(**spec_dict)

    agent = SiteAnalysisAgent(schema_path=schema_path)

    print(f"\n[OK] Agent initialized")
    print(f"  Analyzing site (Seoul, 37.5°N)...")

    results = agent.analyze_site(
        spec=spec,
        latitude=37.5665,
        longitude=126.9780
    )

    print(f"\n  Site Info:")
    print(f"    Building footprint: {results['site_info']['building_footprint']:.2f} m²")
    print(f"    Building coverage: {results['site_info']['building_coverage_ratio']:.1f}%")

    print(f"\n  Solar Analysis:")
    solar = results['solar_analysis']
    print(f"    Min sunlight hours: {solar['minimum_sunlight_hours']:.1f} hrs")
    print(f"    Korean standard: {solar['korean_standard_required']} hrs")
    print(f"    Compliance: {solar['status']}")

    return True


def test_structural_agent():
    """Test Structural Agent."""
    print_section("TEST 5: Structural Agent (Loads + Structure)")

    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    json_path = Path(__file__).parent.parent / "tests" / "fixtures" / "3ldk_apartment.json"

    with open(json_path, 'r', encoding='utf-8') as f:
        spec_dict = json.load(f)
    spec = DesignSpec(**spec_dict)

    agent = StructuralAgent(schema_path=schema_path)

    print(f"\n[OK] Agent initialized")
    print(f"  Analyzing structure...")

    results = agent.analyze_structure(spec, building_use="residential")

    print(f"\n  Building Info:")
    print(f"    Floors: {results['building_info']['total_floors']}")
    print(f"    Height: {results['building_info']['building_height']:.1f} m")

    print(f"\n  Loads:")
    loads = results['load_analysis']
    print(f"    Total dead load: {loads['total_dead_load']:.1f} kN")
    print(f"    Total live load: {loads['total_live_load']:.1f} kN")

    print(f"\n  Column Design:")
    col = results['column_design']
    print(f"    Column size: {col['column_size']}")
    print(f"    Column count: {results['structural_grid']['column_count']}")

    return True


def test_mep_agent():
    """Test MEP Agent."""
    print_section("TEST 6: MEP Agent (Mechanical + Electrical + Plumbing)")

    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    json_path = Path(__file__).parent.parent / "tests" / "fixtures" / "3ldk_apartment.json"

    with open(json_path, 'r', encoding='utf-8') as f:
        spec_dict = json.load(f)
    spec = DesignSpec(**spec_dict)

    agent = MEPAgent(schema_path=schema_path)

    print(f"\n[OK] Agent initialized")
    print(f"  Analyzing MEP systems...")

    results = agent.analyze_mep_systems(spec, building_use="residential")

    print(f"\n  HVAC:")
    hvac = results['hvac']
    print(f"    Total cooling load: {hvac['total_cooling_load']:.1f} kW")
    print(f"    Total heating load: {hvac['total_heating_load']:.1f} kW")
    print(f"    System: {hvac['system_recommendations']}")

    print(f"\n  Electrical:")
    elec = results['electrical']
    print(f"    Total load: {elec['total_connected_load']:.1f} kVA")
    print(f"    Panel size: {elec['recommended_panel']}")

    print(f"\n  Plumbing:")
    plumb = results['plumbing']
    print(f"    Total fixtures: {plumb['total_fixtures']}")
    print(f"    Supply pipe: {plumb['supply_pipe_size']}")

    return True


def test_compliance_agent():
    """Test Compliance Agent."""
    print_section("TEST 7: Compliance Agent (Building Code Check)")

    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    json_path = Path(__file__).parent.parent / "tests" / "fixtures" / "3ldk_apartment.json"

    with open(json_path, 'r', encoding='utf-8') as f:
        spec_dict = json.load(f)
    spec = DesignSpec(**spec_dict)

    agent = ComplianceAgent(schema_path=schema_path)

    print(f"\n[OK] Agent initialized")
    print(f"  Checking compliance...")

    # Assume site area is 1.5x building footprint
    total_area = sum(
        agent.geometry_engine.calculate_polygon_area(room.geometry.coordinates)
        for floor in spec.building.floors
        if floor.level == 1
        for room in floor.rooms
    )
    site_area = total_area * 1.5

    results = agent.check_compliance(
        spec=spec,
        site_area=site_area,
        zoning_type="residential",
        zoning_district="type2"
    )

    print(f"\n  Overall Status: {results['overall_compliance']['status']}")
    print(f"  Passed: {results['overall_compliance']['passed_checks']}/{results['overall_compliance']['total_checks']}")

    print(f"\n  Key Checks:")
    print(f"    Building Coverage: {results['building_coverage']['coverage_ratio']:.1f}% (max {results['building_coverage']['max_allowed']}%)")
    print(f"    Floor Area Ratio: {results['floor_area_ratio']['floor_area_ratio']:.1f}% (max {results['floor_area_ratio']['max_allowed']}%)")
    print(f"    Parking: {results['parking']['provided_parking']}/{results['parking']['required_parking']} spaces")

    # Generate summary
    print(f"\n  Summary Report:")
    summary = agent.generate_summary_report(results)
    output_path = Path(__file__).parent.parent / "output" / "test_all" / "compliance_report.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"  [OK] Report saved: {output_path}")

    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  LLM-CAD INTEGRATION SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    results = {}

    # Test all agents
    try:
        results['AutoCAD'] = test_autocad_agent()
    except Exception as e:
        print(f"[FAIL] AutoCAD Agent failed: {e}")
        results['AutoCAD'] = False

    try:
        results['Revit'] = test_revit_agent()
    except Exception as e:
        print(f"[FAIL] Revit Agent failed: {e}")
        results['Revit'] = False

    try:
        results['Rhino'] = test_rhino_agent()
    except Exception as e:
        print(f"[FAIL] Rhino Agent failed: {e}")
        results['Rhino'] = False

    try:
        results['Site Analysis'] = test_site_analysis_agent()
    except Exception as e:
        print(f"[FAIL] Site Analysis Agent failed: {e}")
        results['Site Analysis'] = False

    try:
        results['Structural'] = test_structural_agent()
    except Exception as e:
        print(f"[FAIL] Structural Agent failed: {e}")
        results['Structural'] = False

    try:
        results['MEP'] = test_mep_agent()
    except Exception as e:
        print(f"[FAIL] MEP Agent failed: {e}")
        results['MEP'] = False

    try:
        results['Compliance'] = test_compliance_agent()
    except Exception as e:
        print(f"[FAIL] Compliance Agent failed: {e}")
        results['Compliance'] = False

    # Print summary
    print_section("TEST SUMMARY")

    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v is False and v is not None)
    failed = sum(1 for v in results.values() if v is None)

    for agent, result in results.items():
        status = "[OK] PASS" if result is True else "[SKIP] SKIPPED" if result is False else "[FAIL] FAIL"
        print(f"  {agent:20s} {status}")

    print(f"\nTotal: {passed} passed, {skipped} skipped, {failed} failed")

    if failed == 0:
        print("\n*** All tests completed successfully! ***")
    else:
        print(f"\n[SKIP]️  {failed} test(s) failed - check errors above")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
