"""
Orchestrator Agent - Main coordinator for LLM-CAD Integration System.

This is the central agent that manages the entire workflow from natural language
input to CAD file generation.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import os

from .conversation_manager import ConversationManager
from .spec_generator import SpecGenerator
from .task_distributor import TaskDistributor, AgentType
from ..models.design_spec import DesignSpec


class OrchestratorAgent:
    """
    Main orchestrator agent that coordinates the entire LLM-CAD workflow.

    Workflow:
    1. Receive natural language input from user
    2. Generate/refine DesignSpec JSON using Claude
    3. Validate specification
    4. Distribute tasks to implementation agents
    5. Collect and present results
    """

    def __init__(
        self,
        schema_path: Path,
        output_dir: Optional[Path] = None,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize orchestrator agent.

        Args:
            schema_path: Path to JSON schema file
            output_dir: Directory for output files
            api_key: Anthropic API key (or from environment)
            session_id: Optional session ID for conversation
        """
        self.schema_path = Path(schema_path)
        self.output_dir = Path(output_dir) if output_dir else Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.conversation = ConversationManager(session_id=session_id)
        self.spec_generator = SpecGenerator(
            schema_path=schema_path,
            api_key=api_key
        )
        self.task_distributor = TaskDistributor(
            schema_path=schema_path,
            output_dir=self.output_dir
        )

        # Current design spec
        self.current_spec: Optional[DesignSpec] = None

    def process_message(
        self,
        user_message: str,
        auto_execute: bool = False
    ) -> Dict[str, Any]:
        """
        Process a message from the user.

        Args:
            user_message: User's natural language input
            auto_execute: If True, automatically execute tasks after spec generation

        Returns:
            Response dictionary with status and content
        """
        # Add user message to conversation
        self.conversation.add_user_message(user_message)

        # Determine action based on conversation phase
        phase = self.conversation.state.phase

        if phase == "initial":
            # Initial spec generation
            return self._handle_initial_request(user_message, auto_execute)
        elif phase == "refinement":
            # Refine existing spec
            return self._handle_refinement(user_message, auto_execute)
        elif phase == "execution":
            # Handle execution-related queries
            return self._handle_execution_query(user_message)
        else:
            # General conversation
            return self._handle_general_query(user_message)

    def _handle_initial_request(
        self,
        user_message: str,
        auto_execute: bool
    ) -> Dict[str, Any]:
        """
        Handle initial design request.

        Args:
            user_message: User's design requirements
            auto_execute: Whether to auto-execute tasks

        Returns:
            Response dictionary
        """
        try:
            # Generate spec from natural language
            spec_dict = self.spec_generator.generate_from_text(user_message)

            # Validate and convert to Pydantic model
            self.current_spec = DesignSpec(**spec_dict)

            # Update conversation state
            self.conversation.update_state(
                design_spec=spec_dict,
                phase="refinement"
            )

            response = {
                'status': 'success',
                'action': 'spec_generated',
                'message': '설계 사양이 생성되었습니다. 검토 후 수정이 필요하면 말씀해주세요.',
                'design_spec': spec_dict,
                'next_steps': [
                    '설계 내용을 검토해주세요',
                    '수정이 필요하면 구체적으로 말씀해주세요',
                    '문제가 없다면 "실행" 또는 "생성"이라고 말씀해주세요'
                ]
            }

            # Save spec to file
            spec_file = self.output_dir / "design_spec.json"
            with open(spec_file, 'w', encoding='utf-8') as f:
                json.dump(spec_dict, f, indent=2, ensure_ascii=False)
            response['spec_file'] = str(spec_file)

            self.conversation.add_assistant_message(
                response['message'],
                metadata={'design_spec': spec_dict}
            )

            # Auto-execute if requested
            if auto_execute:
                exec_result = self.execute_design()
                response['execution'] = exec_result

            return response

        except Exception as e:
            error_msg = f"설계 사양 생성 중 오류 발생: {str(e)}"
            self.conversation.add_assistant_message(error_msg)
            return {
                'status': 'error',
                'action': 'spec_generation_failed',
                'message': error_msg,
                'error': str(e)
            }

    def _handle_refinement(
        self,
        user_message: str,
        auto_execute: bool
    ) -> Dict[str, Any]:
        """
        Handle refinement of existing spec.

        Args:
            user_message: User's refinement request
            auto_execute: Whether to auto-execute tasks

        Returns:
            Response dictionary
        """
        # Check for execution trigger words
        execution_keywords = ['실행', '생성', 'execute', 'generate', 'create', '만들어']
        if any(keyword in user_message.lower() for keyword in execution_keywords):
            return self.execute_design()

        # Otherwise, refine the spec
        try:
            current_spec_dict = self.current_spec.model_dump()
            refined_spec_dict = self.spec_generator.refine_spec(
                current_spec=current_spec_dict,
                feedback=user_message
            )

            # Update current spec
            self.current_spec = DesignSpec(**refined_spec_dict)
            self.conversation.update_state(design_spec=refined_spec_dict)

            response = {
                'status': 'success',
                'action': 'spec_refined',
                'message': '설계 사양이 수정되었습니다. 추가 수정이 필요하거나 실행하려면 말씀해주세요.',
                'design_spec': refined_spec_dict,
                'changes': '사용자 요청에 따라 수정됨'
            }

            # Save updated spec
            spec_file = self.output_dir / "design_spec.json"
            with open(spec_file, 'w', encoding='utf-8') as f:
                json.dump(refined_spec_dict, f, indent=2, ensure_ascii=False)

            self.conversation.add_assistant_message(response['message'])

            # Auto-execute if requested
            if auto_execute:
                exec_result = self.execute_design()
                response['execution'] = exec_result

            return response

        except Exception as e:
            error_msg = f"설계 수정 중 오류 발생: {str(e)}"
            self.conversation.add_assistant_message(error_msg)
            return {
                'status': 'error',
                'action': 'refinement_failed',
                'message': error_msg,
                'error': str(e)
            }

    def _handle_execution_query(self, user_message: str) -> Dict[str, Any]:
        """Handle queries during/after execution."""
        task_status = self.task_distributor.get_task_status()

        response = {
            'status': 'success',
            'action': 'execution_status',
            'message': f"작업 진행 상황: {task_status['by_status']}",
            'task_status': task_status
        }

        self.conversation.add_assistant_message(response['message'])
        return response

    def _handle_general_query(self, user_message: str) -> Dict[str, Any]:
        """Handle general queries."""
        response = {
            'status': 'success',
            'action': 'info',
            'message': '새로운 설계를 시작하려면 건물이나 공간에 대해 설명해주세요.',
            'available_commands': [
                '새 설계 시작',
                '이전 설계 불러오기',
                '도움말'
            ]
        }

        self.conversation.add_assistant_message(response['message'])
        return response

    def execute_design(self) -> Dict[str, Any]:
        """
        Execute the current design specification.

        Returns:
            Execution results
        """
        if not self.current_spec:
            return {
                'status': 'error',
                'message': '실행할 설계 사양이 없습니다. 먼저 설계를 생성해주세요.'
            }

        try:
            # Update phase
            self.conversation.update_state(phase="execution")

            # Analyze requirements and create tasks
            tasks = self.task_distributor.analyze_requirements(self.current_spec)

            # Execute tasks
            results = self.task_distributor.execute_tasks()

            # Update phase
            self.conversation.update_state(phase="complete")

            response = {
                'status': 'success',
                'action': 'execution_complete',
                'message': f"설계 실행 완료! {results['completed']}개 작업 성공, {results['failed']}개 실패",
                'results': results,
                'output_files': [output['result'].get('output_file') for output in results['outputs']]
            }

            self.conversation.add_assistant_message(
                response['message'],
                metadata={'results': results}
            )

            return response

        except Exception as e:
            error_msg = f"실행 중 오류 발생: {str(e)}"
            self.conversation.add_assistant_message(error_msg)
            return {
                'status': 'error',
                'action': 'execution_failed',
                'message': error_msg,
                'error': str(e)
            }

    def get_current_spec(self) -> Optional[Dict[str, Any]]:
        """
        Get current design specification.

        Returns:
            Current design spec as dictionary, or None
        """
        if self.current_spec:
            return self.current_spec.model_dump()
        return None

    def save_spec_to_file(self, output_path: Path):
        """
        Save current specification to file.

        Args:
            output_path: Path to output file
        """
        if not self.current_spec:
            raise ValueError("No design spec to save")

        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_spec.model_dump(), f, indent=2, ensure_ascii=False)

    def load_spec_from_file(self, input_path: Path):
        """
        Load specification from file.

        Args:
            input_path: Path to input file
        """
        input_path = Path(input_path)
        with open(input_path, 'r', encoding='utf-8') as f:
            spec_dict = json.load(f)

        self.current_spec = DesignSpec(**spec_dict)
        self.conversation.update_state(
            design_spec=spec_dict,
            phase="refinement"
        )

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history.

        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in self.conversation.messages]

    def save_session(self):
        """Save current session to disk."""
        session_dir = self.output_dir / "sessions"
        self.conversation.save_session(session_dir)

    def reset(self):
        """Reset orchestrator to initial state."""
        self.conversation.clear()
        self.current_spec = None
        self.task_distributor.clear_tasks()
        self.conversation.update_state(phase="initial")

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get orchestrator capabilities.

        Returns:
            Capabilities dictionary
        """
        return {
            'name': 'Orchestrator Agent',
            'version': '1.0.0',
            'description': 'Main coordinator for LLM-CAD integration',
            'features': [
                'Natural language to JSON conversion',
                'Design specification validation',
                'Multi-agent task distribution',
                'Conversation management',
                'Session persistence'
            ],
            'available_agents': self.task_distributor.get_available_agents(),
            'supported_formats': ['DXF', 'JSON'],
            'api_model': self.spec_generator.model
        }
