"""
LangGraph StateGraph workflow definition and compilation.
"""

from typing import Optional, Any
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from agent.skills import TOOLS
from agent.chain import build_chain, AgentOutputParser

SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are an intelligent AI Assistant with specialized skills in Browsing and Ticket Booking.\n"
        "Your available skills:\n"
        "1. `browse_web`: Look up real-time information, travel schedules, reviews, or URL content.\n"
        "2. `book_ticket`: Make ticket reservations for flights, trains, buses, movies, or events.\n"
        "3. `check_ticket_status`: Verify status of booked reservations.\n\n"
        "Always be helpful, ask clarifying questions if details like dates or passenger names are missing, "
        "and confirm details before booking when appropriate."
    )
)


def build_agent_graph(llm_or_chain: Optional[Any] = None, checkpointer: Optional[MemorySaver] = None):
    """
    Constructs the LangGraph compiled state graph using an LCEL Chain (model | parser)
    with a MemorySaver checkpointer.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    # Resolve chain: keeps model and parser combined in the chain
    if llm_or_chain is None:
        chain = build_chain()
    elif hasattr(llm_or_chain, "bind_tools"):
        # If a raw model is passed, compose it with the parser into the chain
        chain = build_chain(model=llm_or_chain)
    else:
        # Already an LCEL chain (e.g. RunnableSequence)
        chain = llm_or_chain

    def chatbot_node(state: AgentState):
        # Chain executes: prompt/messages -> model -> parser
        messages = [SYSTEM_PROMPT] + state["messages"]
        response = chain.invoke(messages)
        return {"messages": [response]}

    # Build the workflow
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("tools", ToolNode(tools=TOOLS))

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")

    # Compile with MemorySaver object checkpointer
    return graph_builder.compile(checkpointer=checkpointer)

