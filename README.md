# AI Powered Command Terminal

This project is a sophisticated, Python-based command terminal that seamlessly blends traditional direct command execution with the power of a large language model (LLM) agent. It provides a rich, interactive user experience with advanced features like dynamic autocompletion, command history, and natural language command processing.

The agent is built using a modern, scalable architecture with `langgraph-bigtool`, using **Groq** for high-speed LLM inference and a **Milvus** vector database for efficient tool retrieval.

## Core Features

*   **Hybrid Execution Mode**: Run standard shell commands (e.g., `ls -l`, `ping google.com`) for instant execution, or prefix your command with `ai` to delegate complex, multi-step tasks to the AI agent.
*   **Natural Language Processing**: Simply tell the agent what you want to do in plain English (e.g., `ai find all text files modified in the last day and zip them`), and it will reason about the task and execute the necessary commands.
*   **Dynamic Tool Discovery**: On its first run, the terminal automatically scans your system's `PATH`, discovering thousands of available executables and making them available as tools for both the AI agent and the user.
*   **Safety First**: The agent is designed with safety in mind. It is explicitly forbidden from using `sudo`, and a **human-in-the-loop confirmation** is required for potentially destructive operations like `rm` or `mv`.
*   **Advanced Interactive UI**: Built with `prompt-toolkit`, the terminal offers:
    *   Persistent command history (use arrow keys).
    *   Auto-suggestions based on your history.
    *   Dynamic autocompletion for thousands of system commands (press Tab).
*   **Scalable & Fast Architecture**:
    *   Uses `langgraph-bigtool` to efficiently manage a massive number of tools.
    *   Leverages a Milvus vector database for fast Retrieval-Augmented Generation (RAG) of tools.
    *   Powered by the Groq API for extremely fast LLM inference with models like Llama 3.
*   **Optimized for Fast Startups**: After the first run, the tool index and registry are cached, allowing the terminal to start almost instantly on subsequent launches.

## Architecture Overview

The terminal operates in two main modes:

### Direct Command Execution
```
[User Input] -> [main.py] -> [Standard Command] -> [Safe Subprocess Executor] -> [Output]
```

### AI Agent Execution
```
[User
Input] -> [main.py] -> [ai Command] -> [LangGraph Agent] -> [Tool Retriever
(Milvus)] -> [LLM (Groq)] -> [Tool Executor] -> [Final Answer]
```

## Prerequisites

*   Python 3.10+
*   Docker and Docker Compose (for running the Milvus vector database)

## Setup and Installation

1.  **Clone the Repository**
    ```bash
    git clone <your-repository-url>
    cd python-terminal
    ```

2.  **Create a Python Virtual Environment**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Start the Milvus Database**
    Make sure Docker is running, then start the Milvus service in the background:
    ```bash
    docker-compose up -d
    ```

5.  **Configure API Keys**
    Create a `.env` file in the root of the project directory:
    ```bash
    touch .env
    ```
    Open the `.env` file and add your Groq API key:
    ```env
    GROQ_API_KEY="gsk_YourActualGroqApiKeyHere"
    ```

6.  **First-Time Run (Tool Indexing)**
    The first time you run the application, it will perform a one-time setup process to discover all system commands and populate the Milvus database. **This will take several minutes.**
    ```bash
    python main.py
    ```
    You will see output related to "Building Toolset from System PATH," "Creating command tools," and "Populating Milvus index." Subsequent startups will be nearly instant.

## How to Use

Run the terminal from the project's root directory:
```bash
python main.py
```
You will be greeted by the hybrid terminal prompt.

*   **Direct Commands**: Type any standard command and press Enter.
    ```
    (python-terminal) $> ls -a
    (python-terminal) $> git status
    ```
*   **AI Agent Commands**: Prefix your request with `ai`.
    ```
    (python-terminal) $> ai list all files in my home directory sorted by size
    (python-terminal) $> ai create a new folder called 'backups' and copy all .log files into it
    ```
*   **UI Features**:
    *   Press the **Up/Down arrow keys** to navigate your command history.
    *   Press the **Tab key** to autocomplete commands.
    *   Start typing and see a faint suggestion from your history. Press the **Right arrow key** to accept it.

## Project Structure

```
python-terminal/
├── .env                  # Stores API keys and environment variables
├── docker-compose.yml    # Defines the Milvus service for Docker
├── requirements.txt      # Lists all Python dependencies
├── agent/
│   ├── agent_core.py     # Core logic for building and compiling the LangGraph agent
│   └── dynamic_tools.py  # Discovers system commands and wraps them in safe tools
└── main.py               # The main entry point and user interface for the terminal
```

## Troubleshooting

*   **ModuleNotFoundError**: You are likely running `python main.py` from the wrong directory. Make sure you are in the project's root `python-terminal/` directory before executing.
*   **Milvus Connection Errors**: Ensure your Docker daemon is running and that you have started the Milvus container with `docker-compose up -d`.
*   **Slow Startup**: This is expected on the very first run. If it's slow on every run, it may mean the cache file (`.tool_registry.pkl`) is not being created or read correctly. Check file permissions.
