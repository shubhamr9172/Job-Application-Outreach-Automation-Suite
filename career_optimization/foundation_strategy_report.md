# Foundational AI Engineer Strategy Report: Core Concepts & Roadmap

**Candidate**: Shubham Reddy  
**Target Role**: Junior-to-Mid AI Engineer / GenAI Systems Engineer  
**Core Goal**: Master Generative AI primitives, basic architectures, and developer frameworks before advancing to enterprise-scale systems.  
**Analysis Date**: May 21, 2026  

---

## 1. Executive Summary

Transitioning from a traditional **TCS Systems Engineer** role (built on GCP, Python, and SQL) to AI Engineering does not require jumping straight into hyper-complex multi-agent loops or custom model training. The most successful AI Engineers start by mastering **code-first primitives**: calling APIs, structuring prompts, chunking text, querying vector databases, and managing simple loops.

This report outlines the core AI concepts you need to learn, presents a structured **3-Month Foundational Study Plan**, and provides detailed blueprints for **3 Foundational Portfolio Projects** (with code boilerplates and system architectures). 

Once you complete this foundation, you will be fully prepared to execute the advanced projects in the [Career Strategy Report](file:///d:/SR/Main%20Projects/Resume%20Details/career_optimization/career_strategy_report.md).

---

## 2. Core GenAI Concepts Explained Simply

When starting out, AI terminology can feel overwhelming. Below is a simplified breakdown of the five core concepts you must master.

```mermaid
graph TD
    A[Unstructured Text/Files] -->|1. Ingest & Chunk| B[Text Chunks]
    B -->|2. Create Embeddings| C[Embedding Vectors]
    C -->|3. Store & Index| D[Vector Database]
    E[User Query] -->|4. Embed & Query| D
    D -->|5. Retrieve Context| F[Matched Context Chunks]
    F -->|6. Inject into Prompt| G[Large Language Model (LLM)]
    G -->|7. Generate Response| H[User Answer]
```

### 1. Large Language Models (LLMs) & APIs
*   **What they are**: Statistical models trained on vast amounts of text to predict the next word in a sequence.
*   **How we use them**: Instead of running these models locally (which requires expensive GPUs), we use cloud-hosted model APIs (e.g., Google Gemini, OpenAI, Anthropic Claude).
*   **Key Parameters to Control**:
    *   **Temperature** (0.0 to 2.0): Controls "creativity" or randomness. Set it to `0.0` for code extraction or factual Q&A (deterministic), and `0.7` to `1.0` for creative writing or brainstorming.
    *   **System Instructions / System Prompt**: The core instruction that sets the LLM's identity, behavior constraints, and response rules.

### 2. Prompt Engineering
*   **What it is**: The practice of designing input text (prompts) to get the most accurate and formatted response from an LLM.
*   **Core Strategies**:
    *   **Few-Shot Prompting**: Providing 2–3 examples of the desired input and output format inside the prompt so the LLM can copy the pattern.
    *   **Chain-of-Thought (CoT)**: Instructing the LLM to "think step-by-step" before writing the final answer. This dramatically reduces logical errors.
    *   **Structured Outputs**: Using libraries like `Pydantic` and `Instructor` to force the LLM to return data in a clean, parsable JSON format matching a specific database schema.

### 3. Vector Databases (Vector DBs) & Embeddings
*   **Embeddings**: Converting text (words, sentences, documents) into a list of numbers (e.g., `[0.12, -0.45, 0.89, ...]`) called a **Vector**. This vector represents the semantic *meaning* of the text. Similar meanings end up close to each other in mathematical space.
*   **Vector Database**: A database designed specifically to store these numerical vectors and run high-speed searches to find the most "semantically similar" documents to a query (e.g., searching for "IT issues" will find documents containing "system crash" or "network downtime" even if the exact words don't match).
*   **Beginner Database**: **ChromaDB** (runs locally on your machine with 0 setup) or **FAISS**.

### 4. Retrieval-Augmented Generation (RAG)
*   **What it is**: A pattern that gives LLMs access to external, custom data (like your company's PDFs, docs, or wikis) without retraining the model.
*   **The 6-Step Pipeline**:
    1.  **Load**: Read documents (PDF, TXT, HTML).
    2.  **Chunk**: Cut long documents into smaller, overlapping pieces (e.g., 500 characters per chunk).
    3.  **Embed**: Pass chunks through an embedding model to generate vectors.
    4.  **Index**: Store the vectors and text chunks in a Vector DB (like ChromaDB).
    5.  **Retrieve**: When a user asks a question, embed the query, search the Vector DB for the top 3 most similar chunks.
    6.  **Synthesize**: Feed the user's question *and* the retrieved chunks into the LLM, instructing it: *"Answer this question using only the provided context."*

### 5. Basic Agentic Workflows
*   **What they are**: Moving beyond simple single-turn prompts into scripts where the LLM can make decisions, run loops, and execute tools.
*   **Tool Calling / Function Calling**: Letting the LLM decide when to call a helper function (e.g., a calculator, SQL database query, or web search tool) to fetch external data, parse the result, and continue its execution.

---

## 3. 3-Month Foundational Study Plan

This study plan is structured into 6 bi-weekly sprints. Each sprint introduces one core concept, recommends free learning resources, and details a practical micro-exercise.

```
┌────────────────────────────────────────────────────────────────────────┐
│             MONTH 1: LLM APIS, PROMPTING & STRUCTURED DATA             │
├────────────────────────────────────────────────────────────────────────┤
│ • Sprint 1 (Weeks 1-2): Python LLM APIs, parameters, & chat memory.     │
│ • Sprint 2 (Weeks 3-4): Structured JSON Outputs using Pydantic.        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│             MONTH 2: VECTOR DBS & RETRIEVAL (RAG) RUNTIME              │
├────────────────────────────────────────────────────────────────────────┤
│ • Sprint 3 (Weeks 5-6): Chunking, embeddings, and ChromaDB setup.       │
│ • Sprint 4 (Weeks 7-8): Building a naive RAG pipeline with Streamlit.  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│             MONTH 3: AGENTS, TOOL CALLING & WEB INTEGRATION            │
├────────────────────────────────────────────────────────────────────────┤
│ • Sprint 5 (Weeks 9-10): LangGraph state machine & Tool execution.     │
│ • Sprint 6 (Weeks 11-12): FastAPI backend wrappers & deployment.        │
└────────────────────────────────────────────────────────────────────────┘
```

### Sprint 1: Python API Integrations & Core parameters (Weeks 1-2)
*   **Goal**: Learn how to write Python scripts to call LLM APIs, control generation parameters, and maintain conversation state.
*   **Core Focus**: Gemini API or OpenAI API, System Instructions, Temperature, Chat Memory loops.
*   **Recommended Free Resources**:
    *   *DeepLearning.AI*: "ChatGPT Prompt Engineering for Developers" (1 hour, free).
    *   *Google Cloud*: "Introduction to Generative AI Studio" (free lab).
*   **Practical Exercise**: Write a local Python CLI chat script that keeps a conversation history list and responds in a specific persona (e.g., "Sarcastic Linux Admin").

### Sprint 2: Structured Outputs & Pydantic Validation (Weeks 3-4)
*   **Goal**: Force LLMs to return strict, valid JSON matching a Python class schema, handling bad inputs gracefully.
*   **Core Focus**: Pydantic, Instructor library, JSON schema generation, field validation.
*   **Recommended Free Resources**:
    *   *Pydantic Documentation*: Getting Started Guide.
    *   *Instructor Library Cookbook*: Structuring LLM outputs.
*   **Practical Exercise**: Write a script that takes a messy, raw text description of an IT server config (e.g., "The web-server is running on 192.168.1.10 with 16GB RAM and port 80 open") and extracts a clean, validated JSON schema containing IP, RAM, and Open Ports.

### Sprint 3: Documents, Embeddings, & Local Vector DBs (Weeks 5-6)
*   **Goal**: Understand document parsing, chunking algorithms, embedding models, and local vector storage.
*   **Core Focus**: RecursiveCharacterTextSplitter, Embedding Models (e.g., `text-embedding-3-small`), ChromaDB.
*   **Recommended Free Resources**:
    *   *DeepLearning.AI*: "Vector Databases: From Embeddings to Applications" (1 hour, free).
    *   *ChromaDB documentation*: Core Python API guide.
*   **Practical Exercise**: Ingest a folder of 5 text files, split them into chunks of 300 characters with 50 characters overlap, embed them, save them to local Chroma DB, and query them.

### Sprint 4: The Naive RAG Assembly & Simple UI (Weeks 7-8)
*   **Goal**: Build a complete document Q&A pipeline (RAG) and host it via a simple web interface.
*   **Core Focus**: Context injection prompts, hallucination boundaries, Streamlit UI.
*   **Recommended Free Resources**:
    *   *DeepLearning.AI*: "LangChain for LLM Application Development" (1 hour, free).
    *   *Streamlit Documentation*: "Build a basic LLM chat app" tutorial.
*   **Practical Exercise**: Combine Sprint 3's vector lookup with a Streamlit interface. The user uploads a PDF, the app indexes it, and the user can query it using a chat input.

### Sprint 5: Tool Calling & Basic Agent loops (Weeks 9-10)
*   **Goal**: Enable LLMs to call custom Python functions to fetch external runtime data.
*   **Core Focus**: Function declarations, API Tool schemas, LangGraph state management, Routers.
*   **Recommended Free Resources**:
    *   *LangChain Academy*: LangGraph Introduction (free notebook resources).
    *   *DeepLearning.AI*: "Functions, Tools and Agents with LangChain" (free).
*   **Practical Exercise**: Build an agent that has access to two tools: `get_current_time()` and `calculate_math()`. If the user asks "What time is it in Tokyo?", the LLM must choose to execute `get_current_time()` instead of guessing.

### Sprint 6: FastAPI Wrapping & Basic Testing (Weeks 11-12)
*   **Goal**: Expose your AI logic as clean backend APIs and implement manual verification testing.
*   **Core Focus**: FastAPI, API endpoints, Pydantic Request/Response models, simple assert testing.
*   **Recommended Free Resources**:
    *   *FastAPI Tutorial*: User guide in documentation.
*   **Practical Exercise**: Wrap your RAG app or Agent app in a FastAPI endpoint (`/api/chat`). Write a simple Python test file using `pytest` that asserts the endpoint responds with valid structures.

---

## 4. Foundational Portfolio Project Blueprints

To build confidence and demonstrate practical coding capabilities, complete the following three projects in order.

---

### Project 1: NoteQ&A (Naive PDF RAG with Streamlit)

A clean, local desktop application where a user can upload a PDF (e.g., a software manual or study guide) and query its contents using a simple chat UI.

```
┌─────────────────┐      ┌───────────────┐      ┌─────────────────────────┐
│  User Uploads   │─────►│  PyPDF Loader │─────►│ Recursive Splitter      │
│  PDF (Streamlit)│      └───────────────┘      │ (Chunk Size: 500 char)  │
└─────────────────┘                             └───────────┬─────────────┘
                                                            │
                                                            ▼
┌─────────────────┐      ┌───────────────┐      ┌─────────────────────────┐
│ LLM Generates   │◄─────│ Inject Chunks │◄─────│ ChromaDB Semantic Match │
│ Answer (Gemini) │      │  into Prompt  │      │ (Query Embedding Match) │
└─────────────────┘      └───────────────┘      └─────────────────────────┘
```

#### 💡 Core Learning Outcomes
*   How to load and extract text from standard PDF documents.
*   How chunk sizes affect retrieval quality.
*   Integrating vector databases with LLM prompts.

#### 🛠️ Tech Stack
*   **Language**: Python
*   **AI Orchestration**: LangChain
*   **Vector DB**: ChromaDB (run in-memory)
*   **LLM API**: Google Gemini (Free tier API Key)
*   **UI Framework**: Streamlit

#### 📄 Implementation Code Blueprint

Create a file named `app.py` in your scratch workspace:

```python
import streamlit as st
import tempfile
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenAIEmbeddings, ChatGoogleGenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

st.title("📄 NoteQ&A: Chat with your PDF")

# Input for Google API Key
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file and api_key:
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    st.info("Ingesting document... splitting text... generating embeddings...")

    # Load and split PDF
    loader = PyPDFLoader(tmp_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)

    # Initialize embeddings and store in local Chroma DB
    embeddings = GoogleGenAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # Define system prompt
    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know.\n\n"
        "Context: {context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # LLM definition
    llm = ChatGoogleGenAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0.0)

    # Combine RAG chain
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    st.success("Document loaded successfully!")

    # Chat loop interface
    user_query = st.text_input("Ask a question about the document:")
    if user_query:
        with st.spinner("Searching context & generating response..."):
            response = rag_chain.invoke({"input": user_query})
            st.write("**Answer**:", response["answer"])
            
    # Cleanup temporary file
    os.unlink(tmp_path)
```

---

### Project 2: DocuExtract (Structured JSON Data Extractor)

An API service that accepts messy, unstructured text (like raw business emails or server logs) and parses them into a validated, structured JSON schema using Pydantic.

```
┌───────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ Messy Raw Email   │─────►│ Pydantic Schema Defined │─────►│ LLM API JSON Call       │
│  (FastAPI POST)   │      │   (Expected Fields)     │      │   (Structured Output)   │
└───────────────────┘      └─────────────────────────┘      └───────────┬─────────────┘
                                                                        │
                                                                        ▼
┌───────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐
│ Saved to DB / Log │◄─────│ Pydantic Auto-Validates │◄─────│ Messy Text Transformed  │
│ (Validated JSON)  │      │  (Type & Format check)  │      │   to Target Schema      │
└───────────────────┘      └─────────────────────────┘      └─────────────────────────┘
```

#### 💡 Core Learning Outcomes
*   How to force LLMs to output syntactically valid JSON.
*   Data validation using Pydantic schemas.
*   Exposing logic via FastAPI endpoints.

#### 🛠️ Tech Stack
*   **Language**: Python
*   **API Framework**: FastAPI
*   **JSON Parsing**: Pydantic + Instructor
*   **LLM API**: Google Gemini or OpenAI

#### 📄 Implementation Code Blueprint

Create a backend file `server.py` in your scratch workspace:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import google.generativeai as genai
import json

app = FastAPI(title="DocuExtract API")

# Define target data schema we expect to extract
class ServerLogSummary(BaseModel):
    server_name: str = Field(description="Name or ID of the server")
    ip_address: Optional[str] = Field(None, description="IP Address of the server")
    error_code: int = Field(description="HTTP or application error status code (e.g. 500)")
    severity: str = Field(description="Severity levels: CRITICAL, WARNING, INFO")
    affected_services: List[str] = Field(default=[], description="List of services or APIs impacted")
    troubleshooting_steps: List[str] = Field(description="Recommended steps extracted from text to resolve issue")

class ExtractionRequest(BaseModel):
    raw_text: str
    api_key: str

@app.post("/extract-summary", response_model=ServerLogSummary)
async def extract_summary(req: ExtractionRequest):
    if not req.api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
    
    # Configure Gemini SDK
    genai.configure(api_key=req.api_key)
    
    # Formulate structured prompt
    prompt = f"""
    Analyze the following server incident report and extract structured details matching the schema.
    If details are missing, return null for optional fields.
    
    Incident Report Text:
    {req.raw_text}
    """
    
    # We use gemini schema generation to force JSON output
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=ServerLogSummary,
                temperature=0.0
            )
        )
        # Parse result text
        extracted_data = json.loads(response.text)
        return ServerLogSummary(**extracted_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {str(e)}")
```

---

### Project 3: Assistant Lite (LangGraph Router with Web Search & Calculator)

A stateful chatbot that can answer conversational questions, but dynamically routes to external tools (using a calculator for math and web search for current events) when needed.

```
                       ┌─────────────────────────┐
                       │   Incoming User Input   │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │   State/Router Agent    │◄───────────────────┐
                       └────────────┬────────────┘                    │
                                    │                                 │
                    Does the query need external data?                │
                                    ├─── YES (Math) ──► [ Calculator] ┤
                                    ├─── YES (News) ──► [ Web Search] ┤
                                    └─── NO ──────────────────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │  Final Response Output  │
                       └─────────────────────────┘
```

#### 💡 Core Learning Outcomes
*   State management in LLM conversations.
*   Exposing functions to LLMs as runnable tools.
*   Handling tool responses and re-injecting them into LLM contexts.

#### 🛠️ Tech Stack
*   **Language**: Python
*   **Orchestration**: LangGraph
*   **Tools**: Custom Python Functions (Calculator) + Tavily Search API (Web Search)
*   **LLM API**: Google Gemini or OpenAI

#### 📄 Implementation Code Blueprint

Create an agent file `agent.py` in your scratch workspace:

```python
import os
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# 1. Define custom tools the LLM can use
@tool
def calculate_math(expression: str) -> str:
    """Useful to calculate mathematical expressions. Input must be a valid Python expression (e.g. '123 * 45')."""
    try:
        # Simple safe evaluation
        return str(eval(expression, {"__builtins__": None}))
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"

# 2. Package tools
tools = [calculate_math]
tool_node = ToolNode(tools)

# 3. Define Graph State structure
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 4. Set up LangGraph components
def run_agent():
    # Fetch API Key from environment
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set the GEMINI_API_KEY environment variable")
        
    llm = ChatGoogleGenAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0.0)
    llm_with_tools = llm.bind_tools(tools)

    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    # 5. Build Graph
    workflow = StateGraph(State)
    
    # Add nodes representing tasks
    workflow.add_node("chatbot", chatbot)
    workflow.add_node("tools", tool_node)

    # Establish connections
    workflow.add_edge(START, "chatbot")
    
    # Conditional edge: check if tool call is needed
    workflow.add_conditional_edges(
        "chatbot",
        tools_condition,  # Standard utility checking if LLM requested tools
    )
    workflow.add_edge("tools", "chatbot")

    return workflow.compile()

# Example usage local test
if __name__ == "__main__":
    os.environ["GEMINI_API_KEY"] = input("Enter Gemini API Key: ")
    app = run_agent()
    
    # Test query requiring math tool
    inputs = {"messages": [("user", "What is 15632 multiplied by 456?")]}
    for event in app.stream(inputs):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)
```

---

## 5. Bridging the Gap to Advanced Workflows

Completing these foundational projects acts as a direct preparation gate for the high-paying advanced architectures. The skills translate step-by-step:

| Foundational Project | Core Concept Learnt | Bridges Directly To (Advanced Report) | What You'll Add |
| :--- | :--- | :--- | :--- |
| **Project 1: NoteQ&A** | Basic RAG & Vector matching. | **Project 1: Enterprise GraphRAG** | Hierarchical chunks, Neo4j knowledge graphs, and Cohere reranking. |
| **Project 2: DocuExtract** | Pydantic JSON extraction. | **Project 3: Fine-Tuned Domain SLM** | Synthesizing custom datasets, fine-tuning Llama-3 with QLoRA on SageMaker, serving via vLLM. |
| **Project 3: Assistant Lite** | Stateful routing & tool usage. | **Project 2: Self-Evaluating Resolver** | Multi-agent collaboration states, custom Model Context Protocol (MCP) servers, and DeepEval metric evaluation. |

---

## 6. Actionable Next Steps

To begin your learning journey without feeling overwhelmed:
1.  **Get a Free API Key**: Register for a free Google Gemini developer key via Google AI Studio. It allows free-tier execution for up to 15 requests per minute, which is perfect for development.
2.  **Set Up your Local Environment**: Create a dedicated directory on your computer and set up a Python virtual environment:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    pip install streamlit fastapi pydantic langchain-google-genai langgraph
    ```
3.  **Run Project 1 (NoteQ&A)**: Write `app.py`, run it using `streamlit run app.py`, and test it with a simple PDF. Focus on seeing how changes to chunk size change what the model answers.
