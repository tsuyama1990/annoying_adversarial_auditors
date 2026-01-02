from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .graph_nodes import CycleNodes
from .sandbox import SandboxRunner
from .services.jules_client import JulesClient
from .state import CycleState


class GraphBuilder:
    def __init__(self, sandbox_runner: SandboxRunner, jules_client: JulesClient):
        self.nodes = CycleNodes(sandbox_runner, jules_client)

    def _create_architect_graph(self) -> StateGraph:
        """Create the graph for the Architect phase (gen-cycles)."""
        workflow = StateGraph(CycleState)

        workflow.add_node("architect_session", self.nodes.architect_session_node)

        workflow.add_edge(START, "architect_session")
        workflow.add_edge("architect_session", END)

        return workflow

    def _create_coder_graph(self) -> StateGraph:
        """Create the graph for the Coder/Auditor phase (run-cycle)."""
        workflow = StateGraph(CycleState)

        workflow.add_node("coder_session", self.nodes.coder_session_node)
        workflow.add_node("auditor", self.nodes.auditor_node)
        workflow.add_node("uat_evaluate", self.nodes.uat_evaluate_node)

        workflow.add_edge(START, "coder_session")

        # Conditional edge from coder_session
        workflow.add_conditional_edges(
            "coder_session",
            self.nodes.check_coder_outcome,
            {
                "ready_for_audit": "auditor",
                "failed": END,
                "completed": "uat_evaluate",  # Direct to UAT if audit skipped (e.g. iteration 0)
            },
        )

        # Conditional edge from auditor
        workflow.add_conditional_edges(
            "auditor",
            self.nodes.check_audit_outcome,
            {
                "approved": "uat_evaluate",
                "rejected_retry": "coder_session",
                "rejected_max_retries": END,
            },
        )

        workflow.add_edge("uat_evaluate", END)

        return workflow

    def build_architect_graph(self):
        return self._create_architect_graph().compile(checkpointer=MemorySaver())

    def build_coder_graph(self):
        return self._create_coder_graph().compile(checkpointer=MemorySaver())
