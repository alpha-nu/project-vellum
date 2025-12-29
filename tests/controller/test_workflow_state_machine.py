import pytest
from controller.workflow.state_machine import WorkflowState, WorkflowStateMachine

def test_initial_state():
    sm = WorkflowStateMachine()
    assert sm.get_state() == WorkflowState.SOURCE_INPUT
    assert not sm.can_go_back()

def test_forward_and_backwards_transitions():
    sm = WorkflowStateMachine()
    # Forward through all states
    for _ in range(5):
        sm.next()
    assert sm.get_state() == WorkflowState.COMPLETE
    # Backwards through all states
    for _ in range(5):
        sm.back()
    assert sm.get_state() == WorkflowState.SOURCE_INPUT
    assert not sm.can_go_back()

def test_partial_backwards():
    sm = WorkflowStateMachine()
    sm.next() 
    sm.next() 
    sm.next() 
    assert sm.get_state() == WorkflowState.FILES_SELECTION
    sm.back()
    assert sm.get_state() == WorkflowState.MERGE_MODE_SELECTION
    sm.back()
    assert sm.get_state() == WorkflowState.FORMAT_SELECTION
    sm.back()
    assert not sm.can_go_back()

def test_reset():
    sm = WorkflowStateMachine()
    sm.context.files = ["file1", "file2"]
    sm.next()
    sm.next()
    sm.reset()
    assert sm.get_state() == WorkflowState.SOURCE_INPUT
    assert sm.context.files == []
    assert not sm.can_go_back()
