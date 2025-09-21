import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from utils.error_handler import handle_error

# Load environment variables from the .env file in the project root
load_dotenv()

# Check if the API key is available
if not os.getenv("GROQ_API_KEY"):
    handle_error(
        "Groq API key not found. Please create a .env file with your GROQ_API_KEY."
    )
    # Set a flag or handle the absence of the key as needed
    langchain_is_configured = False
else:
    langchain_is_configured = True


def get_translation_chain():
    """
    Builds and returns a LangChain chain for translating natural language to shell commands.
    """
    # 1. The Prompt Template
    # This defines the instructions and context for the AI model.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert assistant. Your sole purpose is to translate a user's natural language request into a single, valid, and executable shell command for a standard Linux/macOS environment. Provide ONLY the command, with no explanation, comments, or markdown formatting.",
            ),
            ("user", "{query}"),
        ]
    )

    # 2. The Model
    # This is the Groq language model we'll be using. gpt-oss-20b is fast and effective.
    # temperature=0 makes the output deterministic and reliable for commands.
    model = ChatGroq(model="openai/gpt-oss-20b", temperature=0)

    # 3. The Output Parser
    # This takes the AI's response and extracts just the string content.
    output_parser = StrOutputParser()

    # 4. The Chain
    # We chain these components together using the LangChain Expression Language (LCEL).
    # The user's query flows from the prompt to the model, and the model's output is then parsed.
    return prompt | model | output_parser


# Initialize the chain only if configured
if langchain_is_configured:
    chain = get_translation_chain()


def translate_to_command(query: str):
    """
    Translates a natural language query into a shell command using a LangChain chain.
    """
    if not langchain_is_configured:
        handle_error(
            "AI feature is disabled. Please configure your Groq API key in the .env file."
        )
        return None

    try:
        # 'invoke' runs the chain with the given input.
        # The input is a dictionary where the key matches the placeholder in the prompt ('query').
        command = chain.invoke({"query": query})
        return command.strip()
    except Exception as e:
        handle_error(f"LangChain/Groq Error: Could not process the query. {e}")
        return None
