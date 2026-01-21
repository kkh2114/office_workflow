"""
Task Distributor for Orchestrator Agent.

Distributes tasks to appropriate implementation agents based on design spec.
"""

from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from enum import Enum
import json

from ..models.design_spec import DesignSpec
from ..agents.autocad_agent import AutoCADAgent


class AgentType(Enum):
    """Available implementation agent types."""
    AUTOCAD = "autocad"
    REVIT = "revit"
    RHINO = "rhino"
    SITE_ANALYSIS = "site_analysis"
    STRUCTURAL = "structural"
    MEP = "mep"
    COMPLIANCE = "compliance"


class Task:
    """Represents a task to be executed by an agent."""

    def __init__(
        self,
        task_id: str,
        agent_type: AgentType,
        action: str,
        parameters: Dict[str, Any],
        priority: int = 0,
        dependencies: Optional[List[str]] = None
    ):
        self.task_id = task_id
        self.agent_type = agent_type
        self.action = action
        self.parameters = parameters
        self.priority = priority
        self.dependencies = dependencies or []
        self.status = "pending"  # pending, running, completed, failed
        self.result: Optional[Any] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            'task_id': self.task_id,
            'agent_type': self.agent_type.value,
            'action': self.action,
            'parameters': self.parameters,
            'priority': self.priority,
            'dependencies': self.dependencies,
            'status': self.status,
            'result': self.result,
            'error': self.error
        }


class TaskDistributor:
    """
    Distributes tasks to implementation agents.

    Responsibilities:
    - Analyze design spec to determine required tasks
    - Create tasks for appropriate agents
    - Manage task dependencies
    - Execute tasks in correct order
    - Collect and aggregate results
    """

    def __init__(
        self,
        schema_path: Path,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize task distributor.

        Args:
            schema_path: Path to JSON schema file
            output_dir: Directory for output files
        """
        self.schema_path = Path(schema_path)
        self.output_dir = Path(output_dir) if output_dir else Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize available agents
        self.agents: Dict[AgentType, Any] = {}
        self._initialize_agents()

        # Task tracking
        self.tasks: List[Task] = []
        self.task_counter = 0

    def _initialize_agents(self):
        """Initialize available implementation agents."""
        # AutoCAD Agent (always available)
        self.agents[AgentType.AUTOCAD] = AutoCADAgent(schema_path=self.schema_path)

        # Other agents will be initialized when implemented
        # self.agents[AgentType.REVIT] = RevitAgent(...)
        # self.agents[AgentType.RHINO] = RhinoAgent(...)

    def analyze_requirements(self, design_spec: DesignSpec) -> List[Task]:
        """
        Analyze design specification and generate task list.

        Args:
            design_spec: Design specification

        Returns:
            List of tasks to execute
        """
        tasks = []

        # Task 1: Generate 2D floor plans (AutoCAD)
        for floor in design_spec.building.floors:
            task_id = self._generate_task_id()
            task = Task(
                task_id=task_id,
                agent_type=AgentType.AUTOCAD,
                action="create_floor_plan",
                parameters={
                    "design_spec": design_spec.model_dump(),
                    "floor_level": floor.level,
                    "output_path": str(self.output_dir / f"floor_{floor.level}.dxf")
                },
                priority=1
            )
            tasks.append(task)

        # Additional tasks will be added as more agents are implemented
        # Example: 3D BIM model (Revit)
        # if self._is_agent_available(AgentType.REVIT):
        #     task = Task(...)
        #     tasks.append(task)

        self.tasks.extend(tasks)
        return tasks

    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        self.task_counter += 1
        return f"task_{self.task_counter:04d}"

    def _is_agent_available(self, agent_type: AgentType) -> bool:
        """Check if an agent is available."""
        return agent_type in self.agents

    def execute_tasks(self) -> Dict[str, Any]:
        """
        Execute all pending tasks.

        Returns:
            Dictionary containing execution results
        """
        results = {
            'total_tasks': len(self.tasks),
            'completed': 0,
            'failed': 0,
            'outputs': []
        }

        # Sort tasks by priority (higher first)
        sorted_tasks = sorted(self.tasks, key=lambda t: t.priority, reverse=True)

        for task in sorted_tasks:
            if task.status != "pending":
                continue

            # Check dependencies
            if not self._check_dependencies(task):
                task.status = "failed"
                task.error = "Unmet dependencies"
                results['failed'] += 1
                continue

            # Execute task
            try:
                task.status = "running"
                result = self._execute_task(task)
                task.status = "completed"
                task.result = result
                results['completed'] += 1
                results['outputs'].append({
                    'task_id': task.task_id,
                    'agent': task.agent_type.value,
                    'action': task.action,
                    'result': result
                })
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                results['failed'] += 1

        return results

    def _check_dependencies(self, task: Task) -> bool:
        """
        Check if task dependencies are met.

        Args:
            task: Task to check

        Returns:
            True if all dependencies are completed
        """
        if not task.dependencies:
            return True

        for dep_id in task.dependencies:
            dep_task = next((t for t in self.tasks if t.task_id == dep_id), None)
            if not dep_task or dep_task.status != "completed":
                return False

        return True

    def _execute_task(self, task: Task) -> Any:
        """
        Execute a single task.

        Args:
            task: Task to execute

        Returns:
            Task execution result

        Raises:
            ValueError: If agent not available or action unknown
        """
        if not self._is_agent_available(task.agent_type):
            raise ValueError(f"Agent {task.agent_type.value} not available")

        agent = self.agents[task.agent_type]

        # Execute based on agent type and action
        if task.agent_type == AgentType.AUTOCAD:
            return self._execute_autocad_task(agent, task)
        # Add more agent types as they are implemented
        # elif task.agent_type == AgentType.REVIT:
        #     return self._execute_revit_task(agent, task)

        raise ValueError(f"Unknown agent type: {task.agent_type}")

    def _execute_autocad_task(self, agent: AutoCADAgent, task: Task) -> Dict[str, Any]:
        """
        Execute AutoCAD agent task.

        Args:
            agent: AutoCAD agent instance
            task: Task to execute

        Returns:
            Execution result
        """
        action = task.action
        params = task.parameters

        if action == "create_floor_plan":
            # Convert dict back to DesignSpec
            design_spec = DesignSpec(**params['design_spec'])

            # Generate floor plan
            output_path = Path(params['output_path'])
            agent.create_floor_plan(
                spec=design_spec,
                output_path=output_path,
                floor_level=params['floor_level']
            )

            # Analyze result
            analysis = agent.analyze_floor_plan(design_spec, params['floor_level'])

            return {
                'output_file': str(output_path),
                'analysis': analysis,
                'status': 'success'
            }

        raise ValueError(f"Unknown AutoCAD action: {action}")

    def add_task(
        self,
        agent_type: AgentType,
        action: str,
        parameters: Dict[str, Any],
        priority: int = 0,
        dependencies: Optional[List[str]] = None
    ) -> Task:
        """
        Add a new task.

        Args:
            agent_type: Type of agent to use
            action: Action to perform
            parameters: Action parameters
            priority: Task priority (higher = earlier)
            dependencies: List of task IDs this depends on

        Returns:
            Created task
        """
        task_id = self._generate_task_id()
        task = Task(
            task_id=task_id,
            agent_type=agent_type,
            action=action,
            parameters=parameters,
            priority=priority,
            dependencies=dependencies
        )
        self.tasks.append(task)
        return task

    def get_task_status(self) -> Dict[str, Any]:
        """
        Get status of all tasks.

        Returns:
            Task status summary
        """
        status_counts = {
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0
        }

        for task in self.tasks:
            status_counts[task.status] += 1

        return {
            'total': len(self.tasks),
            'by_status': status_counts,
            'tasks': [task.to_dict() for task in self.tasks]
        }

    def clear_tasks(self):
        """Clear all tasks."""
        self.tasks.clear()
        self.task_counter = 0

    def get_available_agents(self) -> List[str]:
        """
        Get list of available agent types.

        Returns:
            List of agent type names
        """
        return [agent_type.value for agent_type in self.agents.keys()]
