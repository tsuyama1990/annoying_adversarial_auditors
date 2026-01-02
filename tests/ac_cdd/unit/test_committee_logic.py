import pytest
from unittest.mock import MagicMock
from ac_cdd_core.graph_nodes import CycleNodes
from ac_cdd_core.state import CycleState
from ac_cdd_core.domain_models import AuditResult

@pytest.mark.asyncio
async def test_committee_logic_flow():
    # Mock settings
    mock_settings = MagicMock()
    mock_settings.NUM_AUDITORS = 3
    mock_settings.REVIEWS_PER_AUDITOR = 2

    # Instantiate nodes with mocks
    sandbox = MagicMock()
    jules = MagicMock()

    # We need to patch where settings is used.
    # graph_nodes.py does `from .config import settings` at top level.
    # So we must patch ac_cdd_core.graph_nodes.settings
    with pytest.MonkeyPatch.context() as m:
        m.setattr("ac_cdd_core.graph_nodes.settings", mock_settings)

        nodes = CycleNodes(sandbox, jules)

        # --- Scenario 1: All Approved (Happy Path) ---
        # Auditor 1: Approved
        state = CycleState(cycle_id="1", current_auditor_index=1, current_auditor_review_count=1)
        state.audit_result = AuditResult(status="APPROVED", is_approved=True, reason="OK", feedback="LGTM")

        res = await nodes.committee_manager_node(state)
        assert res["status"] == "next_auditor"
        assert res["current_auditor_index"] == 2
        assert res["current_auditor_review_count"] == 1

        # Check routing
        route = nodes.route_committee({"status": "next_auditor"})
        assert route == "auditor"

        # Auditor 2: Approved
        state.current_auditor_index = 2
        res = await nodes.committee_manager_node(state)
        assert res["status"] == "next_auditor"
        assert res["current_auditor_index"] == 3

        # Auditor 3: Approved (Last one)
        state.current_auditor_index = 3
        res = await nodes.committee_manager_node(state)
        assert res["status"] == "cycle_approved"

        # Check routing - Expecting 'uat_evaluate' per requirements
        route = nodes.route_committee({"status": "cycle_approved"})
        assert route == "uat_evaluate"

        # --- Scenario 2: Rejected & Retry (Loop Back) ---
        # Auditor 2: Rejected (Attempt 1 of 2)
        state = CycleState(cycle_id="2", current_auditor_index=2, current_auditor_review_count=1, iteration_count=5)
        state.audit_result = AuditResult(status="REJECTED", is_approved=False, reason="Issues found", feedback="Fix this")

        res = await nodes.committee_manager_node(state)
        assert res["status"] == "retry_fix"
        assert res["current_auditor_review_count"] == 2
        assert res["iteration_count"] == 6 # Should increment iteration

        route = nodes.route_committee({"status": "retry_fix"})
        assert route == "coder_session"

        # --- Scenario 3: Max Retries Exceeded (Failure) ---
        # Auditor 2: Rejected (Attempt 2 of 2)
        state = CycleState(cycle_id="3", current_auditor_index=2, current_auditor_review_count=2)
        state.audit_result = AuditResult(status="REJECTED", is_approved=False, reason="Still bad", feedback="Still broken")

        res = await nodes.committee_manager_node(state)
        assert res["status"] == "failed"

        route = nodes.route_committee({"status": "failed"})
        assert route == "failed"
