from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING, Callable
from enum import Enum, auto
from typing import Dict

from controller.path_protocol import PathLike
from view.output_format import OutputFormat
from view.merge_mode import MergeMode
from domain.core.output_handler import OutputHandler
from domain.model.file import File

@dataclass
class WorkflowContext:
    input_path: Optional['PathLike'] = None
    format_choice: Optional['OutputFormat'] = None
    merge_mode: Optional['MergeMode'] = None
    files: List['File'] = field(default_factory=list)
    handler: Optional['OutputHandler'] = None
    merged_filename: Optional[str] = None
    error_message: Optional[str] = None
    error_origin: Optional['WorkflowState'] = None

class WorkflowState(Enum):
    SOURCE_INPUT = auto()
    FORMAT_SELECTION = auto()
    MERGE_MODE_SELECTION = auto()
    FILES_SELECTION = auto()
    PROCESSING = auto()
    COMPLETE = auto()
    ERROR = auto()

@dataclass(frozen=True)
class StateTransition:
    next: Optional['WorkflowState']
    back: Optional['WorkflowState']

WORKFLOW_TRANSITIONS: Dict[WorkflowState, StateTransition] = {
    WorkflowState.SOURCE_INPUT: StateTransition(WorkflowState.FORMAT_SELECTION, None),
    WorkflowState.FORMAT_SELECTION: StateTransition(WorkflowState.MERGE_MODE_SELECTION, WorkflowState.SOURCE_INPUT),
    WorkflowState.MERGE_MODE_SELECTION: StateTransition(WorkflowState.FILES_SELECTION, WorkflowState.FORMAT_SELECTION),
    WorkflowState.FILES_SELECTION: StateTransition(WorkflowState.PROCESSING, WorkflowState.MERGE_MODE_SELECTION),
    WorkflowState.PROCESSING: StateTransition(WorkflowState.COMPLETE, None),
    WorkflowState.COMPLETE: StateTransition(WorkflowState.SOURCE_INPUT, None),
    WorkflowState.ERROR: StateTransition(WorkflowState.SOURCE_INPUT, None),
}

class ConversionWorkflow:
    def __init__(self, initial_state: WorkflowState = WorkflowState.SOURCE_INPUT, on_state_change: Optional[Callable[[], None]] = None):
        self.state = initial_state
        self.state_stack: List[WorkflowState] = []
        self.context = WorkflowContext()
        self._on_state_change = on_state_change

    def next(self) -> None:
        transition = WORKFLOW_TRANSITIONS[self.state]
        if transition.next is not None:
            self.state_stack.append(self.state)
            self.state = transition.next
            if self._on_state_change:
                self._on_state_change()

    def back(self) -> None:
        if self.state_stack:
            self.state = self.state_stack.pop()
            if self._on_state_change:
                self._on_state_change()

    def can_go_back(self) -> bool:
        return bool(self.state_stack)

    def reset(self):
        self.state = WorkflowState.SOURCE_INPUT
        self.state_stack.clear()
        self.context = WorkflowContext()
        if self._on_state_change:
            self._on_state_change()

    def get_state(self) -> WorkflowState:
        return self.state
