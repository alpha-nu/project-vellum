from dataclasses import dataclass, field

# Holds all mutable, shared workflow data
@dataclass
class WorkflowContext:
    input_path: any = None
    format_choice: any = None
    merge_mode: any = None
    files: list = field(default_factory=list)
    handler: any = None
    merged_filename: any = None
    # Add more fields as needed for workflow
from enum import Enum, auto
from typing import Callable, Dict, Optional, List, Any
from dataclasses import dataclass

class WorkflowState(Enum):
    SOURCE_INPUT = auto()
    FORMAT_SELECTION = auto()
    MERGE_MODE_SELECTION = auto()
    FILES_SELECTION = auto()
    PROCESSING = auto()
    COMPLETE = auto()


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
}


class WorkflowStateMachine:
    def __init__(self, initial_state: WorkflowState = WorkflowState.SOURCE_INPUT):
        self.state = initial_state
        self.state_stack: List[WorkflowState] = []
        self.context = WorkflowContext()

    def next(self) -> None:
        transition = WORKFLOW_TRANSITIONS[self.state]
        if transition.next is not None:
            self.state_stack.append(self.state)
            self.state = transition.next

    def back(self) -> None:
        if self.state_stack:
            self.state = self.state_stack.pop()

    def can_go_back(self) -> bool:
        return bool(self.state_stack)

    def reset(self):
        self.state = WorkflowState.SOURCE_INPUT
        self.state_stack.clear()
        self.context = WorkflowContext()

    def get_state(self) -> WorkflowState:
        return self.state
