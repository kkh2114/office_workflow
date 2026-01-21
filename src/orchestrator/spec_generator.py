"""
Spec Generator for Orchestrator Agent.

Converts natural language descriptions into structured DesignSpec JSON.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import os
from anthropic import Anthropic
from pydantic import ValidationError

from ..models.design_spec import DesignSpec
from ..skills.schema_validator import SchemaValidator


class SpecGenerator:
    """
    Generates DesignSpec JSON from natural language using Claude API.

    Responsibilities:
    - Parse natural language design requirements
    - Generate structured JSON specifications
    - Validate generated specs against schema
    - Refine specs based on feedback
    """

    def __init__(
        self,
        schema_path: Path,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022"
    ):
        """
        Initialize spec generator.

        Args:
            schema_path: Path to JSON schema file
            api_key: Anthropic API key (or from environment)
            model: Claude model to use
        """
        self.schema_path = Path(schema_path)
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or provided")

        self.client = Anthropic(api_key=self.api_key)
        self.validator = SchemaValidator(schema_path)

        # Load schema for context
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)

    def _build_system_prompt(self) -> str:
        """
        Build system prompt for Claude.

        Returns:
            System prompt string
        """
        return """You are an expert architectural design assistant. Your role is to convert natural language descriptions of buildings and spaces into structured JSON specifications following the DesignSpec schema.

Key responsibilities:
1. Extract spatial requirements (rooms, dimensions, layout)
2. Identify design elements (doors, windows, furniture)
3. Capture project metadata (name, client, requirements)
4. Generate valid, complete JSON specifications
5. Ask clarifying questions when requirements are ambiguous

Design principles:
- All dimensions are in METERS
- Coordinates use [x, y] format
- Polygons must be CLOSED (first point == last point)
- Room types: living_room, bedroom, kitchen, bathroom, etc.
- Door/window placement uses wall_index (0=bottom, 1=right, 2=top, 3=left)

Always respond with valid JSON that strictly follows the schema. If information is missing, make reasonable assumptions or ask for clarification."""

    def _build_generation_prompt(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build prompt for JSON generation.

        Args:
            user_input: Natural language input from user
            context: Optional context from previous conversation

        Returns:
            Formatted prompt
        """
        prompt_parts = [
            "Please convert the following architectural design requirements into a valid DesignSpec JSON:",
            "",
            f"User Requirements:\n{user_input}",
            ""
        ]

        if context:
            prompt_parts.extend([
                "Additional Context:",
                json.dumps(context, indent=2),
                ""
            ])

        prompt_parts.extend([
            "Generate a complete DesignSpec JSON that includes:",
            "1. project_info (name, description, client)",
            "2. building with floors",
            "3. Each floor with rooms",
            "4. Each room with:",
            "   - geometry (polygon coordinates in meters)",
            "   - doors (with wall_index and position)",
            "   - windows (with wall_index, position, dimensions)",
            "   - furniture (optional)",
            "",
            "Important:",
            "- All coordinates in METERS",
            "- Polygons MUST be closed (first point == last point)",
            "- Use realistic dimensions for Korean residential spaces",
            "- Place doors/windows logically on appropriate walls",
            "",
            "Respond with ONLY the JSON, no additional text."
        ])

        return "\n".join(prompt_parts)

    def _build_refinement_prompt(
        self,
        current_spec: Dict[str, Any],
        feedback: str
    ) -> str:
        """
        Build prompt for refining existing spec.

        Args:
            current_spec: Current design specification
            feedback: User feedback for refinement

        Returns:
            Formatted prompt
        """
        return f"""Here is the current design specification:

{json.dumps(current_spec, indent=2, ensure_ascii=False)}

User Feedback:
{feedback}

Please update the specification based on this feedback. Maintain all existing data unless specifically requested to change it. Respond with the complete updated JSON."""

    def generate_from_text(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 8000
    ) -> Dict[str, Any]:
        """
        Generate DesignSpec JSON from natural language.

        Args:
            user_input: Natural language description
            context: Optional context from conversation
            max_tokens: Maximum tokens for response

        Returns:
            Generated design specification as dictionary

        Raises:
            ValueError: If generation fails or JSON is invalid
        """
        prompt = self._build_generation_prompt(user_input, context)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self._build_system_prompt(),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract JSON from response
            response_text = response.content[0].text
            spec_json = self._extract_json(response_text)

            # Validate against schema
            validation_result = self.validator.validate_json(spec_json)
            if not validation_result['valid']:
                raise ValueError(f"Generated spec failed validation: {validation_result['errors']}")

            return spec_json

        except Exception as e:
            raise ValueError(f"Failed to generate spec: {str(e)}")

    def refine_spec(
        self,
        current_spec: Dict[str, Any],
        feedback: str,
        max_tokens: int = 8000
    ) -> Dict[str, Any]:
        """
        Refine existing specification based on feedback.

        Args:
            current_spec: Current design specification
            feedback: User feedback
            max_tokens: Maximum tokens for response

        Returns:
            Refined design specification

        Raises:
            ValueError: If refinement fails
        """
        prompt = self._build_refinement_prompt(current_spec, feedback)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self._build_system_prompt(),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = response.content[0].text
            refined_spec = self._extract_json(response_text)

            # Validate refined spec
            validation_result = self.validator.validate_json(refined_spec)
            if not validation_result['valid']:
                raise ValueError(f"Refined spec failed validation: {validation_result['errors']}")

            return refined_spec

        except Exception as e:
            raise ValueError(f"Failed to refine spec: {str(e)}")

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from text response.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON as dictionary

        Raises:
            ValueError: If no valid JSON found
        """
        # Try to parse entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block between ```json and ```
        import re
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        # Try to find any JSON-like structure
        brace_start = text.find('{')
        brace_end = text.rfind('}')
        if brace_start != -1 and brace_end != -1:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError("Could not extract valid JSON from response")

    def validate_and_convert(self, spec_dict: Dict[str, Any]) -> DesignSpec:
        """
        Validate JSON and convert to Pydantic model.

        Args:
            spec_dict: Design specification dictionary

        Returns:
            Validated DesignSpec model

        Raises:
            ValidationError: If validation fails
        """
        try:
            return DesignSpec(**spec_dict)
        except ValidationError as e:
            raise ValueError(f"Spec validation failed: {str(e)}")

    def generate_example_spec(self, room_count: int = 3) -> Dict[str, Any]:
        """
        Generate an example specification for testing.

        Args:
            room_count: Number of rooms to include

        Returns:
            Example design specification
        """
        example = {
            "project_info": {
                "name": "Example Project",
                "description": f"Example {room_count}-room apartment",
                "client": "Example Client",
                "location": "Seoul, South Korea",
                "requirements": ["Natural lighting", "Open layout"]
            },
            "building": {
                "floors": [
                    {
                        "level": 1,
                        "name": "Ground Floor",
                        "height": 2.8,
                        "rooms": []
                    }
                ]
            }
        }

        # Add example rooms
        room_configs = [
            ("거실", "living_room", [[0, 0], [6, 0], [6, 4], [0, 4], [0, 0]]),
            ("침실", "bedroom", [[6, 0], [10, 0], [10, 3], [6, 3], [6, 0]]),
            ("주방", "kitchen", [[0, 4], [4, 4], [4, 6], [0, 6], [0, 4]]),
        ]

        for i, (name, room_type, coords) in enumerate(room_configs[:room_count]):
            room = {
                "name": name,
                "type": room_type,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coords
                },
                "doors": [
                    {
                        "wall_index": 0,
                        "position": 0.5,
                        "width": 0.9,
                        "type": "single"
                    }
                ],
                "windows": [],
                "furniture": []
            }
            example["building"]["floors"][0]["rooms"].append(room)

        return example
