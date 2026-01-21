"""
Conversation Manager for Orchestrator Agent.

Manages conversation state, history, and context for multi-turn interactions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path


class Message:
    """Represents a single message in the conversation."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.role = role  # 'user', 'assistant', 'system'
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


class ConversationState:
    """Represents the current state of the conversation."""

    def __init__(self):
        self.design_spec: Optional[Dict[str, Any]] = None
        self.active_tasks: List[str] = []
        self.completed_tasks: List[str] = []
        self.context: Dict[str, Any] = {}
        self.phase: str = "initial"  # initial, spec_creation, refinement, execution, complete

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            'design_spec': self.design_spec,
            'active_tasks': self.active_tasks,
            'completed_tasks': self.completed_tasks,
            'context': self.context,
            'phase': self.phase
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create state from dictionary."""
        state = cls()
        state.design_spec = data.get('design_spec')
        state.active_tasks = data.get('active_tasks', [])
        state.completed_tasks = data.get('completed_tasks', [])
        state.context = data.get('context', {})
        state.phase = data.get('phase', 'initial')
        return state


class ConversationManager:
    """
    Manages conversation history and state for the orchestrator.

    Responsibilities:
    - Store conversation history
    - Track conversation state (current design spec, active tasks, etc.)
    - Provide context for LLM prompts
    - Save/load conversation sessions
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize conversation manager.

        Args:
            session_id: Optional session identifier for persistence
        """
        self.session_id = session_id or self._generate_session_id()
        self.messages: List[Message] = []
        self.state = ConversationState()
        self.created_at = datetime.now()

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Add a message to the conversation history.

        Args:
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Optional metadata

        Returns:
            The created message
        """
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        return message

    def add_user_message(self, content: str) -> Message:
        """Add a user message."""
        return self.add_message('user', content)

    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add an assistant message."""
        return self.add_message('assistant', content, metadata)

    def add_system_message(self, content: str) -> Message:
        """Add a system message."""
        return self.add_message('system', content)

    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """
        Get the most recent messages.

        Args:
            count: Number of messages to retrieve

        Returns:
            List of recent messages
        """
        return self.messages[-count:] if count < len(self.messages) else self.messages

    def get_messages_for_llm(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """
        Get messages formatted for Claude API.

        Args:
            max_messages: Maximum number of messages to include

        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        recent_messages = self.get_recent_messages(max_messages)
        return [
            {'role': msg.role, 'content': msg.content}
            for msg in recent_messages
            if msg.role in ['user', 'assistant']  # Exclude system messages
        ]

    def update_state(
        self,
        design_spec: Optional[Dict[str, Any]] = None,
        phase: Optional[str] = None,
        context_updates: Optional[Dict[str, Any]] = None
    ):
        """
        Update conversation state.

        Args:
            design_spec: Updated design specification
            phase: New conversation phase
            context_updates: Updates to context dictionary
        """
        if design_spec is not None:
            self.state.design_spec = design_spec

        if phase is not None:
            self.state.phase = phase

        if context_updates:
            self.state.context.update(context_updates)

    def add_task(self, task_id: str):
        """Add a task to active tasks."""
        if task_id not in self.state.active_tasks:
            self.state.active_tasks.append(task_id)

    def complete_task(self, task_id: str):
        """Mark a task as completed."""
        if task_id in self.state.active_tasks:
            self.state.active_tasks.remove(task_id)
        if task_id not in self.state.completed_tasks:
            self.state.completed_tasks.append(task_id)

    def get_conversation_summary(self) -> str:
        """
        Generate a summary of the conversation for context.

        Returns:
            Summary string
        """
        summary_parts = [
            f"Session ID: {self.session_id}",
            f"Phase: {self.state.phase}",
            f"Messages: {len(self.messages)}",
            f"Active Tasks: {len(self.state.active_tasks)}",
            f"Completed Tasks: {len(self.state.completed_tasks)}",
        ]

        if self.state.design_spec:
            summary_parts.append("Design Spec: Created")

        return "\n".join(summary_parts)

    def save_session(self, output_dir: Path):
        """
        Save conversation session to disk.

        Args:
            output_dir: Directory to save session data
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        session_file = output_dir / f"{self.session_id}.json"

        session_data = {
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'messages': [msg.to_dict() for msg in self.messages],
            'state': self.state.to_dict()
        }

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_session(cls, session_file: Path) -> 'ConversationManager':
        """
        Load conversation session from disk.

        Args:
            session_file: Path to session file

        Returns:
            Loaded conversation manager
        """
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        manager = cls(session_id=session_data['session_id'])
        manager.created_at = datetime.fromisoformat(session_data['created_at'])
        manager.messages = [Message.from_dict(msg) for msg in session_data['messages']]
        manager.state = ConversationState.from_dict(session_data['state'])

        return manager

    def clear(self):
        """Clear conversation history and state."""
        self.messages.clear()
        self.state = ConversationState()
