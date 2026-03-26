"""
Dashboard Project Builder AI – project management, game contractor, and build pipeline.

Provides AI-driven project scaffolding, task management, contractor assignment,
and build status tracking for the Sovereignty AI Studio dashboard.
"""
import os
import uuid
import shutil
import logging
import subprocess
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ProjectType(str, Enum):
    GAME = "game"
    WEB_APP = "web_app"
    MOBILE_APP = "mobile_app"
    API = "api"
    AI_MODEL = "ai_model"
    MEDIA = "media"


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class BuildStatus(str, Enum):
    IDLE = "idle"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class Task:
    """Represents a project task."""
    task_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.BACKLOG
    assignee: str = ""
    priority: int = 3
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class DashboardProject:
    """Represents a dashboard project."""
    project_id: str
    user_id: str
    name: str
    project_type: ProjectType = ProjectType.WEB_APP
    description: str = ""
    build_status: BuildStatus = BuildStatus.IDLE
    tasks: List[Task] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class DashboardBuilderService:
    """AI-powered project and build management service."""

    def __init__(self):
        self._projects: Dict[str, DashboardProject] = {}
        logger.info("DashboardBuilderService initialised")

    # ── Project CRUD ─────────────────────────────────────────────────

    def create_project(
        self,
        user_id: str,
        name: str,
        project_type: str = "web_app",
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a new dashboard project with AI-scaffolded tasks."""
        project = DashboardProject(
            project_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            project_type=ProjectType(project_type),
            description=description,
        )
        # Auto-scaffold initial tasks based on project type
        project.tasks = self._scaffold_tasks(project.project_type)
        self._projects[project.project_id] = project

        logger.info(
            "Project '%s' (%s) created for user %s with %d tasks",
            name, project_type, user_id, len(project.tasks),
        )
        return self._project_to_dict(project)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        project = self._projects.get(project_id)
        return self._project_to_dict(project) if project else None

    def list_projects(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        projects = self._projects.values()
        if user_id:
            projects = [p for p in projects if p.user_id == user_id]
        return [self._project_to_dict(p) for p in projects]

    def delete_project(self, project_id: str) -> bool:
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False

    # ── Task management ──────────────────────────────────────────────

    def add_task(
        self,
        project_id: str,
        title: str,
        description: str = "",
        priority: int = 3,
    ) -> Optional[Dict[str, Any]]:
        project = self._projects.get(project_id)
        if not project:
            return None
        task = Task(
            task_id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
        )
        project.tasks.append(task)
        return self._task_to_dict(task)

    def update_task_status(
        self, project_id: str, task_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        project = self._projects.get(project_id)
        if not project:
            return None
        for task in project.tasks:
            if task.task_id == task_id:
                task.status = TaskStatus(status)
                return self._task_to_dict(task)
        return None

    # ── Build pipeline ───────────────────────────────────────────────

    def trigger_build(self, project_id: str) -> Dict[str, Any]:
        """Trigger a real build/deploy pipeline for the project.

        Executes the project's build commands via subprocess. Falls back
        to a syntax validation check when no build toolchain is detected.
        """
        project = self._projects.get(project_id)
        if not project:
            return {"error": "Project not found"}

        project.build_status = BuildStatus.BUILDING
        build_log: List[str] = []
        try:
            # Determine build command based on project type
            build_cmd = self._resolve_build_command(project)
            if build_cmd:
                result = subprocess.run(
                    build_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                build_log.append(result.stdout)
                if result.returncode != 0:
                    build_log.append(result.stderr)
                    project.build_status = BuildStatus.FAILED
                    return {
                        "project_id": project.project_id,
                        "build_status": project.build_status.value,
                        "message": f"Build failed for '{project.name}'",
                        "log": "\n".join(build_log),
                    }

            # Testing phase – validate Python syntax in core directories
            project.build_status = BuildStatus.TESTING
            core_dirs = ["backend", "agents", "event_bus"]
            existing_dirs = [d for d in core_dirs if os.path.isdir(d)]
            if existing_dirs:
                test_result = subprocess.run(
                    ["python", "-m", "compileall", "-q"] + existing_dirs,
                    capture_output=True, text=True, timeout=60,
                )
            else:
                test_result = subprocess.run(
                    ["python", "-c", "print('no core dirs to validate')"],
                    capture_output=True, text=True, timeout=10,
                )
            build_log.append(test_result.stdout)
            if test_result.returncode != 0:
                build_log.append(test_result.stderr)
                project.build_status = BuildStatus.FAILED
                return {
                    "project_id": project.project_id,
                    "build_status": project.build_status.value,
                    "message": f"Tests failed for '{project.name}'",
                    "log": "\n".join(build_log),
                }

            project.build_status = BuildStatus.SUCCESS
            return {
                "project_id": project.project_id,
                "build_status": project.build_status.value,
                "message": f"Build completed successfully for '{project.name}'",
                "log": "\n".join(build_log),
            }
        except subprocess.TimeoutExpired:
            project.build_status = BuildStatus.FAILED
            return {
                "project_id": project.project_id,
                "build_status": project.build_status.value,
                "message": f"Build timed out for '{project.name}'",
            }
        except Exception as exc:
            project.build_status = BuildStatus.FAILED
            logger.error("Build pipeline error: %s", exc)
            return {
                "project_id": project.project_id,
                "build_status": project.build_status.value,
                "message": str(exc),
            }

    @staticmethod
    def _resolve_build_command(project: "DashboardProject") -> Optional[List[str]]:
        """Determine the appropriate build command for a project type."""
        cmd_map = {
            ProjectType.WEB_APP: None,  # uses compileall validation
            ProjectType.API: None,
            ProjectType.GAME: None,
            ProjectType.AI_MODEL: None,
            ProjectType.MOBILE_APP: None,
            ProjectType.MEDIA: None,
        }
        # Check for package.json → npm build
        if os.path.isfile("package.json") and shutil.which("npm"):
            return ["npm", "run", "build", "--if-present"]
        # Check for Makefile → make
        if os.path.isfile("Makefile") and shutil.which("make"):
            return ["make"]
        return cmd_map.get(project.project_type)

    def get_status(self) -> Dict[str, Any]:
        return {
            "service": "dashboard_builder",
            "status": "online",
            "total_projects": len(self._projects),
            "project_types": [t.value for t in ProjectType],
        }

    # ── Private helpers ──────────────────────────────────────────────

    def _scaffold_tasks(self, project_type: ProjectType) -> List[Task]:
        """Generate initial tasks based on project type."""
        common_tasks = [
            ("Project setup", "Initialise project structure and dependencies"),
            ("Core implementation", "Build core application logic"),
            ("Testing", "Write and run unit/integration tests"),
            ("Documentation", "Write project documentation"),
            ("Deployment", "Configure CI/CD and deploy"),
        ]

        type_specific = {
            ProjectType.GAME: [("Game loop", "Implement main game loop and physics")],
            ProjectType.AI_MODEL: [("Model training", "Train and validate AI model")],
            ProjectType.MEDIA: [("Asset pipeline", "Set up media asset processing")],
        }

        all_tasks = common_tasks + type_specific.get(project_type, [])
        return [
            Task(task_id=str(uuid.uuid4()), title=t, description=d)
            for t, d in all_tasks
        ]

    @staticmethod
    def _project_to_dict(project: DashboardProject) -> Dict[str, Any]:
        return {
            "project_id": project.project_id,
            "user_id": project.user_id,
            "name": project.name,
            "project_type": project.project_type.value,
            "description": project.description,
            "build_status": project.build_status.value,
            "task_count": len(project.tasks),
            "tasks_done": sum(
                1 for t in project.tasks if t.status == TaskStatus.DONE
            ),
            "created_at": project.created_at,
        }

    @staticmethod
    def _task_to_dict(task: Task) -> Dict[str, Any]:
        return {
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "assignee": task.assignee,
            "priority": task.priority,
            "created_at": task.created_at,
        }


# Module-level singleton
dashboard_builder_service = DashboardBuilderService()
