import os
import uuid
import subprocess
import platform
import pickle
from dotenv import load_dotenv

# UI imports
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

# Agent and Tool imports
from agent.agent_core import create_bigtool_agent, TOOL_REGISTRY_CACHE_PATH, load_tool_registry_from_cache
from agent.dynamic_tools import load_system_command_tools

def safe_direct_execute(command_string: str) -> str:
    if not command_string: return ""
    parts = command_string.strip().split()
    command_name = parts[0].lower()
    if command_name == 'sudo': return "Error: sudo access is forbidden."
    try:
        result = subprocess.run(parts, capture_output=True, text=True, timeout=30, errors='ignore')
        output = ""
        if result.stdout: output += result.stdout
        if result.stderr: output += f"STDERR:\n{result.stderr}"
        return output
    except FileNotFoundError: return f"Error: Command '{command_name}' not found."
    except Exception as e: return f"An error occurred: {e}"

def get_autocomplete_list() -> list:
    """Gets the list of command names for autocompletion, using cache if available."""
    # Try to load from cache first
    cached_registry = load_tool_registry_from_cache()
    if cached_registry is not None:
        try:
            return [tool.name for tool in cached_registry.values()]
        except Exception as e:
            print(f"Warning: Could not extract tool names from cache: {e}")
    
    # Fallback to slower method if cache loading fails
    print("Loading tools for autocomplete (this may take a moment)...")
    try:
        return [tool.name for tool in load_system_command_tools()]
    except Exception as e:
        print(f"Warning: Could not load tools for autocomplete: {e}")
        return ["ai", "exit", "quit", "clear"]  # Return basic commands as fallback

def execute_agent_query(app, query, config):
    """
    Execute an agent query with better error handling and response extraction.
    Supports both streaming and non-streaming responses.
    """
    final_answer = None
    step_count = 0
    tool_calls = []
    
    try:
        # Try to use invoke first (non-streaming) for more reliable results
        try:
            print(" L AI Agent is working...")
            result = app.invoke({"messages": [("human", query)]}, config)
            
            if result and 'messages' in result:
                messages = result['messages']
                if messages:
                    final_message = messages[-1]
                    if hasattr(final_message, 'content'):
                        final_answer = final_message.content
                        print(f"Debug: Got response via invoke: {final_answer[:100]}...")
        
        except Exception as invoke_error:
            print(f"Debug: Invoke failed ({invoke_error}), trying streaming...")
            
            # Fallback to streaming if invoke fails
            for event in app.stream({"messages": [("human", query)]}, config):
                step_count += 1
                print(f"Debug: Step {step_count} - Event keys: {list(event.keys())}")
                
                for key, value in event.items():
                    if key == "__end__":
                        if 'messages' in value and value['messages']:
                            final_answer_message = value['messages'][-1]
                            if hasattr(final_answer_message, 'content'):
                                final_answer = final_answer_message.content
                                print(f"Debug: Found final answer via streaming: {final_answer[:100]}...")
                    elif key != "__start__" and key != "__end__":
                        # Track tool calls for debugging
                        if 'messages' in value:
                            messages = value.get('messages', [])
                            for msg in messages:
                                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                    tool_calls.extend([tc.get('name', 'unknown') for tc in msg.tool_calls])
                                elif hasattr(msg, 'content') and msg.content:
                                    print(f"Debug: Agent step {key}: {msg.content[:150]}...")
        
        return final_answer, tool_calls, step_count
        
    except Exception as e:
        print(f"Error during agent execution: {e}")
        import traceback
        traceback.print_exc()
        return None, tool_calls, step_count

def main():
    """The main REPL loop for the hybrid AI and Direct Command Terminal."""
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found in .env file. Please set it.")
        return

    try:
        app = create_bigtool_agent()
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return

    # Dynamic Autocompletion
    try:
        print("Loading commands for autocompletion...")
        command_names = get_autocomplete_list()
        command_names.extend(["ai", "exit", "quit", "clear"]) 
        completer = WordCompleter(command_names, ignore_case=True)
        print(f"✅ Autocompletion enabled for {len(command_names)} commands.")
    except Exception as e:
        print(f"⚠️ Could not load dynamic commands for autocompletion: {e}")
        completer = WordCompleter(["ai", "exit", "quit", "clear"], ignore_case=True)

    history = FileHistory(os.path.expanduser("~/.python_agent_terminal_history"))
    session = PromptSession(history=history, auto_suggest=AutoSuggestFromHistory())
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("\n🤖 Hybrid AI Terminal is ready.")
    print("   - Type a command directly (e.g., 'ls -l').")
    print("   - Use 'ai' for complex tasks (e.g., 'ai list all python files').")
    print("   - Press Tab for autocompletion. Type 'exit' to quit.")

    while True:
        try:
            current_dir_prompt = f"({os.path.basename(os.getcwd())}) $> "
            user_input = session.prompt(current_dir_prompt, completer=completer)

            if not user_input.strip(): continue
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting terminal. Goodbye!")
                break
            if user_input.lower() == 'clear':
                os.system('cls' if platform.system() == 'Windows' else 'clear')
                continue

            if user_input.strip().lower().startswith("ai "):
                query = user_input.strip()[3:]
                
                # Add a special test command to verify tools are working
                if query.lower().startswith("test tools"):
                    print("Testing tool registry...")
                    try:
                        # Load the registry to test a tool directly
                        from agent.agent_core import load_tool_registry_from_cache
                        registry = load_tool_registry_from_cache()
                        if registry:
                            # Find relevant tools
                            mkdir_tool = None
                            mv_tool = None
                            ls_tool = None
                            found_tools = []
                            
                            for tool_id, tool in registry.items():
                                if tool.name == 'mkdir':
                                    mkdir_tool = tool
                                elif tool.name in ['mv', 'move']:
                                    mv_tool = tool
                                elif tool.name == 'ls':
                                    ls_tool = tool
                                
                                # Collect all tools with relevant names
                                if any(keyword in tool.name.lower() for keyword in ['mkdir', 'mv', 'move', 'cp', 'copy']):
                                    found_tools.append(tool.name)
                            
                            print(f"Found {len(found_tools)} relevant file operation tools: {', '.join(found_tools[:10])}")
                            
                            if mkdir_tool:
                                print("Testing mkdir tool directly...")
                                print(f"mkdir description: {mkdir_tool.description[:200]}...")
                                result = mkdir_tool.func("test_direct")
                                print(f"mkdir result: {result}")
                                
                            if mv_tool:
                                print(f"Testing {mv_tool.name} tool directly...")
                                print(f"{mv_tool.name} description: {mv_tool.description[:200]}...")
                                
                            if ls_tool:
                                print("Testing ls tool directly...")
                                result = ls_tool.func("-la")
                                print(f"ls result: {result[:200]}...")
                            else:
                                print("ls tool not found")
                                
                            # Test search manually using the existing app's vector store
                            print("\n--- Testing Manual Search ---")
                            try:
                                # Get the vector store from the existing app
                                store = app.store  # This should be the MilvusStoreWrapper
                                if hasattr(store, 'search'):
                                    search_queries = [
                                        "create directory mkdir", 
                                        "move file mv", 
                                        "make folder",
                                        "file operations",
                                        "mkdir",
                                        "mv"
                                    ]
                                    
                                    for search_query in search_queries:
                                        print(f"\nSearching for: '{search_query}'")
                                        results = store.search(query=search_query, k=5)
                                        for i, result in enumerate(results[:3]):
                                            tool_id = result.key
                                            tool = registry.get(tool_id)
                                            tool_name = tool.name if tool else "Unknown"
                                            print(f"  {i+1}. {tool_name} (score: {result.score:.3f})")
                                else:
                                    print("Store doesn't have search method")
                            except Exception as search_error:
                                print(f"Search test failed: {search_error}")
                        else:
                            print("No registry found")
                    except Exception as e:
                        print(f"Tool test error: {e}")
                        import traceback
                        traceback.print_exc()
                    continue
                
                final_answer, tool_calls, step_count = execute_agent_query(app, query, config)
                
                if final_answer:
                    print("\n--- AI Agent Response ---")
                    print(final_answer)
                    print("-------------------------\n")
                else:
                    print("The agent finished without providing a final answer.")
                    if tool_calls:
                        print(f"Tools called: {', '.join(set(tool_calls))}")
                    print(f"Total steps executed: {step_count}")
            else:
                output = safe_direct_execute(user_input)
                if output:
                    print(output)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting terminal. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()