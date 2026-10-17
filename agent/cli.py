"""
Interactive Command-Line Runner for the LangGraph Agent.
"""

import sys
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from env.config import get_gemini_api_key, config
from agent.llm import get_llm, build_chain, ACTIVE_LLM
from agent.graph import build_agent_graph


def main():
    """Runs interactive CLI loop with MemorySaver checkpointer on thread_id='1'."""
    # Ensure Windows console encoding compatibility
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("=" * 60)
    print(f" LangGraph AI Agent [LCEL Chain: model | parser] (LLM: {ACTIVE_LLM})")
    print("=" * 60)

    print(f"\nInitializing {ACTIVE_LLM.upper()} Chain and LangGraph Workflow with MemorySaver...")
    chain = build_chain()

    # Apply memory through MemorySaver object checkpointer
    memory = MemorySaver()
    agent = build_agent_graph(chain, checkpointer=memory)

    # Thread config: invoke using thread=1
    thread_id = config.default_thread_id
    thread_config = {"configurable": {"thread_id": thread_id}}
    print(f"Agent ready with MemorySaver checkpointer on thread_id='{thread_id}'!")
    print("Type 'exit' or 'quit' to terminate.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            # Invoke agent using thread_id=1 in config
            state = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=thread_config,
            )
            latest_messages = state.get("messages", [])

            if latest_messages:
                last_msg = latest_messages[-1]
                print(f"\nAgent: {last_msg.content}\n")

        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
