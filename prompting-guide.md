### 1. `ROUTER_PROMPT`
**Role:** The Traffic Cop 🚦
**Responsibility:** To determine if a user's question is simple (requiring just one search) or complex (requiring multiple searches to connect the dots).
**Usage Guide:**
*   **Where it's used:** In [src/agent/nodes.py](cci:7://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:0:0-0:0) by the [router_node](cci:1://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:19:0-24:62).
*   **How it works:** It forces the LLM to output a strict JSON true/false boolean ([RouteDecision](cci:2://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:7:0-8:158)). 
*   **When to edit:** If you find the agent is over-complicating simple questions (e.g., trying to multi-hop a basic "What is the speed of light?" question), you tighten this prompt to be more restrictive.
*   *Example adjustment:* `"Only return True if the question explicitly asks to compare two different entities."*

### 2. `DECOMPOSER_PROMPT`
**Role:** The Strategist 🗺️
**Responsibility:** If the `ROUTER_PROMPT` decides a question is complex, this prompt breaks the big question down into 2 or 3 smaller, highly targeted search queries.
**Usage Guide:**
*   **Where it's used:** In [src/agent/nodes.py](cci:7://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:0:0-0:0) by the [decomposer_node](cci:1://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:26:0-34:42).
*   **How it works:** It takes a question like "How does the CEO of Apple's salary compare to Microsoft's CEO?" and outputs a JSON array: `["Who is the CEO of Apple and what is their salary?", "Who is the CEO of Microsoft and what is their salary?"]`.
*   **When to edit:** If the agent generates bad sub-queries that the vector database can't understand.
*   *Example adjustment:* `"Break this question down into exactly 3 sub-queries. Ensure each sub-query contains a specific noun or company name."*

### 3. `EVALUATOR_PROMPT`
**Role:** The Judge ⚖️
**Responsibility:** Stops the agent from searching forever. It looks at the context retrieved from PGVector and Neo4j and decides if there is enough factual information to answer the original question.
**Usage Guide:**
*   **Where it's used:** In [src/agent/nodes.py](cci:7://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:0:0-0:0) by the [evaluator_node](cci:1://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:36:0-47:78).
*   **How it works:** It acts as the gatekeeper in the `LangGraph` cyclical loop. If it returns `True`, the loop stops and moves to Synthesis. If `False`, the loop repeats to find more data (up to the `MAX_HOP_COUNT`).
*   **When to edit:** If your agent hallucinates answers because it stopped searching too early, make this prompt stricter.
*   *Example adjustment:* `"You must be 100% certain the context fully answers the question. If there is ANY ambiguity or missing data, you MUST return False."*

### 4. `SYNTHESIZER_PROMPT` (The Master Prompt)
**Role:** The Final Speaker 🎤
**Responsibility:** Takes all the messy, disjointed text chunks from PGVector and the relationships from Neo4j, and writes the beautiful, human-readable final answer that is sent back to the user's screen.
**Usage Guide:**
*   **Where it's used:** In [src/agent/nodes.py](cci:7://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:0:0-0:0) by the [synthesizer_node](cci:1://file:///g:/advanced-multi-hop-rag/src/agent/nodes.py:49:0-55:43).
*   **How it works:** This is standard Chat generation. It has the user's question and a massive block of text containing all retrieved data. It generates the final markdown string.
*   **When to edit:** **Constantly.** This dictates the personality, formatting, and safety rules of your application.
*   *Example adjustment:* `"You are a formal banking assistant. You must format your answer using markdown tables whenever comparing numbers. Always end your response with 'Is there anything else I can help you with?'"*

### 5. `KNOWLEDGE_GRAPH_EXTRACTION_PROMPT`
**Role:** The Data Miner ⛏️
**Responsibility:** Used strictly during data ingestion (File Uploads). It reads chunks of raw documents and extracts structured Graph Nodes and Edges to power Neo4j.
**Usage Guide:**
*   **Where it's used:** In [src/ingestion/extractor.py](cci:7://file:///g:/advanced-multi-hop-rag/src/ingestion/extractor.py:0:0-0:0) by the [parse_with_llm](cci:1://file:///g:/advanced-multi-hop-rag/src/ingestion/extractor.py:7:0-32:22) function.
*   **How it works:** It forces the LLM to output structured Pydantic data that exactly matches your database schema.
*   **When to edit:** When you want to change what kind of intelligence your Knowledge Graph stores! 
*   *Example adjustment:* If you are building a medical RAG app, you would change the allowed nodes here: `"Nodes MUST be one of: Patient, Disease, Medication, Symptom."`

---

## Security & Safety Guardrails 🛡️

To prevent prompt injections, enforce strict formatting, and gracefully handle hallucinations, all agent prompts now automatically append a centralized Guardrail variable. 

These variables are defined at the top of `src/prompts.py` so they can be managed independently of the prompt logic:

*   **`ROUTER_GUARDRAIL`**: Instructs the LLM to ignore bypass instructions and classify injection attempts as simple requests.
*   **`DECOMPOSER_GUARDRAIL`**: Strictly bans the decomposer from answering the core query, ensuring it only outputs the JSON array of sub-questions.
*   **`EVALUATOR_GUARDRAIL`**: Forces the evaluator to only evaluate context sufficiency and ignore adversarial commands buried inside retrieved documents.
*   **`SYNTHESIZER_GUARDRAIL`**: The strongest guardrail. It forces the final speaker to explicitly refuse harmful, illegal, or unethical requests, ignore prompt injections inside the context, and aggressively avoid hallucinations.
*   **`EXTRACTION_GUARDRAIL`**: Ensures the ingestion engine ignores injected text inside uploaded files, forcing it to purely extract the requested graph data. 