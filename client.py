import asyncio
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
import re
import ast
load_dotenv()


async def chat_loop():
    client = MultiServerMCPClient(
        {
            "Crypto": {
                "command": "python",
                "args": ["crypto_server/crypto.py"],
                "transport": "stdio",
            },
            "Chess": {
                "command": "python",
                "args": ["chess_server/chessserver.py"],
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()
    llm = ChatGroq(model="qwen-qwq-32b")
    print("Type 'exit' or 'quit' to stop the chat.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Chat ended.")
            break
        scratchpad = ""
        llm_context = user_input
        while True:
            tool_list = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
            llm_prompt = (
                f"You are an assistant with access to the following tools.\n"
                f"TOOLS:\n{tool_list}\n"
                f"Given the user question and the previous tool results, decide which tool to use and what arguments to provide, or answer the user directly if possible.\n"
                f"If you need to use a tool, return your answer in this format (JSON):\n"
                f"{{'tool': <tool_name>, 'args': <args_dict>}}\n"
                f"If you can answer directly, just output the answer.\n"
                f"User question: {user_input}\n"
                f"Previous tool results: {scratchpad}"
            )
            llm_response = await llm.ainvoke(llm_prompt)
            content = llm_response.content.strip()
            # Find all lines that look like a dict
            dict_lines = [line for line in content.splitlines() if line.strip().startswith("{") and line.strip().endswith("}")]
            if dict_lines:
                json_like = dict_lines[-1]
                try:
                    tool_decision = ast.literal_eval(json_like)
                    tool_name = tool_decision['tool']
                    tool_args = tool_decision['args']
                    tool = next((t for t in tools if t.name == tool_name), None)
                    if not tool:
                        print(f"❗ Tool '{tool_name}' not found.")
                        break
                    result = await tool.ainvoke(tool_args)
                    scratchpad += f"Tool: {tool_name}, Args: {tool_args}, Result: {result}\n"
                    continue  # Loop again with updated scratchpad
                except Exception as e:
                    print(f"❗ Error parsing LLM/tool output: {e}\nRaw LLM output: {content}")
                    break
            else:
                # No tool call, treat as final answer
                print(f"Bot: {content}")
                break


def main():
    asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
