"""
Test script for Orchestrator Agent.

This script demonstrates the end-to-end workflow:
1. Natural language input
2. JSON spec generation
3. Task distribution and execution
"""

from pathlib import Path
import sys
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import OrchestratorAgent


def test_basic_workflow():
    """Test basic orchestrator workflow."""
    print("=" * 60)
    print("Orchestrator Agent Test")
    print("=" * 60)

    # Initialize orchestrator
    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    output_dir = Path(__file__).parent.parent / "output" / "orchestrator_test"

    print("\n1. Initializing Orchestrator Agent...")
    orchestrator = OrchestratorAgent(
        schema_path=schema_path,
        output_dir=output_dir
    )

    # Display capabilities
    capabilities = orchestrator.get_capabilities()
    print("\nCapabilities:")
    print(json.dumps(capabilities, indent=2, ensure_ascii=False))

    # Test 1: Generate spec from natural language
    print("\n" + "=" * 60)
    print("Test 1: Generate Design from Natural Language")
    print("=" * 60)

    user_request = """
    서울에 위치한 30평 아파트를 설계해주세요.

    요구사항:
    - 거실: 약 20평방미터, 남향
    - 안방: 약 15평방미터, 화장실 포함
    - 작은방: 약 10평방미터
    - 주방: 거실과 연결된 개방형
    - 현관에서 거실로 바로 연결
    """

    print(f"\nUser Request:\n{user_request}")
    print("\nGenerating design specification...")

    # Note: This will fail without ANTHROPIC_API_KEY
    try:
        response = orchestrator.process_message(user_request, auto_execute=False)

        print("\nResponse:")
        print(f"Status: {response['status']}")
        print(f"Action: {response['action']}")
        print(f"Message: {response['message']}")

        if response['status'] == 'success':
            print(f"\nDesign spec saved to: {response.get('spec_file')}")

            # Display summary
            spec = response.get('design_spec')
            if spec:
                print("\nDesign Summary:")
                print(f"  Project: {spec['project_info']['name']}")
                print(f"  Floors: {len(spec['building']['floors'])}")
                floor = spec['building']['floors'][0]
                print(f"  Rooms on Floor 1: {len(floor['rooms'])}")
                for room in floor['rooms']:
                    print(f"    - {room['name']} ({room['type']})")

            # Test 2: Execute design
            print("\n" + "=" * 60)
            print("Test 2: Execute Design")
            print("=" * 60)

            exec_response = orchestrator.execute_design()
            print(f"\nExecution Status: {exec_response['status']}")
            print(f"Message: {exec_response['message']}")

            if exec_response['status'] == 'success':
                print("\nGenerated Files:")
                for output_file in exec_response.get('output_files', []):
                    print(f"  - {output_file}")

    except ValueError as e:
        if "ANTHROPIC_API_KEY" in str(e):
            print("\n⚠️  ANTHROPIC_API_KEY not found!")
            print("To test with actual Claude API:")
            print("1. Copy .env.example to .env")
            print("2. Add your Anthropic API key")
            print("3. Run this test again")
            print("\nFalling back to example spec...")

            # Use example spec instead
            test_with_example_spec(orchestrator)
        else:
            raise

    # Save session
    print("\n" + "=" * 60)
    print("Saving session...")
    orchestrator.save_session()
    print("Session saved!")


def test_with_example_spec(orchestrator: OrchestratorAgent):
    """Test with pre-made example spec (no API needed)."""
    print("\n" + "=" * 60)
    print("Testing with Example Specification")
    print("=" * 60)

    # Load existing example
    example_file = Path(__file__).parent.parent / "tests" / "fixtures" / "3ldk_apartment.json"

    print(f"\nLoading example from: {example_file}")
    orchestrator.load_spec_from_file(example_file)

    print("Example spec loaded successfully!")

    # Get current spec
    spec = orchestrator.get_current_spec()
    print("\nDesign Summary:")
    print(f"  Project: {spec['project_info']['name']}")
    print(f"  Floors: {len(spec['building']['floors'])}")
    floor = spec['building']['floors'][0]
    print(f"  Rooms on Floor 1: {len(floor['rooms'])}")
    for room in floor['rooms']:
        print(f"    - {room['name']} ({room['type']})")

    # Execute design
    print("\n" + "=" * 60)
    print("Executing Design...")
    print("=" * 60)

    exec_response = orchestrator.execute_design()
    print(f"\nExecution Status: {exec_response['status']}")
    print(f"Message: {exec_response['message']}")

    if exec_response['status'] == 'success':
        print("\nGenerated Files:")
        for output_file in exec_response.get('output_files', []):
            print(f"  - {output_file}")

        print("\n✅ Test completed successfully!")


def test_conversation_flow():
    """Test multi-turn conversation."""
    print("\n" + "=" * 60)
    print("Test: Multi-turn Conversation")
    print("=" * 60)

    schema_path = Path(__file__).parent.parent / "config" / "schemas" / "design_spec.schema.json"
    output_dir = Path(__file__).parent.parent / "output" / "conversation_test"

    orchestrator = OrchestratorAgent(
        schema_path=schema_path,
        output_dir=output_dir
    )

    # Load example spec
    example_file = Path(__file__).parent.parent / "tests" / "fixtures" / "simple_room.json"
    orchestrator.load_spec_from_file(example_file)

    print("\nInitial spec loaded.")

    # Simulate refinement conversation
    print("\n--- User: 거실을 더 크게 만들어주세요 ---")
    # Note: This would normally refine the spec, but without API key it will fail gracefully

    # Get conversation history
    history = orchestrator.get_conversation_history()
    print(f"\nConversation has {len(history)} messages")


if __name__ == "__main__":
    print("Starting Orchestrator Agent Tests\n")

    try:
        # Test basic workflow
        test_basic_workflow()

        # Test conversation flow
        # test_conversation_flow()

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
