import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from ac_cdd_core.graph import GraphBuilder
from ac_cdd_core.state import CycleState
from langgraph.graph.state import CompiledStateGraph

@pytest.fixture
def mock_sandbox():
    sandbox = MagicMock()
    # Mock run_command to return success tuple
    sandbox.run_command = AsyncMock(return_value=("PASS", "", 0))
    return sandbox

@pytest.fixture
def mock_jules():
    client = MagicMock()
    # Mock methods used in graph nodes
    client.start_architect_session = AsyncMock(return_value={"status": "success"})
    client.run_session = AsyncMock(return_value={"status": "success", "pr_url": "http://pr", "session_name": "sess-123"})
    client.continue_session = AsyncMock(return_value={"status": "success", "pr_url": "http://pr"})
    return client

@pytest.fixture
def graph_builder(mock_sandbox, mock_jules):
    # Updated GraphBuilder signature: (sandbox_runner, jules_client)
    return GraphBuilder(mock_sandbox, mock_jules)

@pytest.mark.asyncio
async def test_architect_graph_structure(graph_builder):
    """Test that architect graph is built correctly."""
    graph = graph_builder.build_architect_graph()
    assert isinstance(graph, CompiledStateGraph)

@pytest.mark.asyncio
async def test_coder_graph_structure(graph_builder):
    """Test that coder graph is built correctly."""
    graph = graph_builder.build_coder_graph()
    assert isinstance(graph, CompiledStateGraph)

@pytest.mark.asyncio
async def test_architect_graph_execution(graph_builder):
    """Test architect graph execution flow."""
    graph = graph_builder.build_architect_graph()
    initial_state = CycleState(cycle_id="00", session_id="test-session")

    # We rely on the mocks injected into GraphBuilder -> CycleNodes
    result = await graph.ainvoke(initial_state)
    assert result["status"] == "architect_completed"

@pytest.mark.asyncio
async def test_coder_graph_execution(mock_sandbox, mock_jules):
    """Test coder graph execution flow."""
    initial_state = CycleState(cycle_id="01", iteration_count=0)
    
    # We need to control AuditOrchestrator to ensure the graph finishes.
    # Since CycleNodes instantiates AuditOrchestrator internally, we patch it.
    with patch("ac_cdd_core.graph_nodes.AuditOrchestrator") as MockAuditClass:
        mock_audit_instance = MockAuditClass.return_value
        # Configure audit to APPROVE so the cycle completes
        mock_result = MagicMock()
        mock_result.status = "approved"
        mock_audit_instance.run_audit = AsyncMock(return_value=mock_result)
        
        # Instantiate builder inside the patch context so it uses the mocked Auditor
        builder = GraphBuilder(mock_sandbox, mock_jules)
        graph = builder.build_coder_graph()

        result = await graph.ainvoke(initial_state)

        assert result["status"] == "cycle_completed"
