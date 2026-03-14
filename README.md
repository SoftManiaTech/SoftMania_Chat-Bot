---
title: SoftMania Chat-Bot
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# SoftMania Chat-Bot 🚀

Welcome to **SoftMania Chat-Bot**, a next-generation intelligence engine designed for deep reasoning over complex document sets. SoftMania goes beyond simple keyword matching, using a multi-layered reasoning architecture to synthesize answers from across your entire knowledge base.

## 🗝️ Core Capabilities

- **🧠 Deep Reasoning (Multi-Hop)**: SoftMania can answer complex questions that require connecting multiple isolated facts across different documents.
- **🗺️ Relationship Mapping**: Built-in Knowledge Graph integration allows the bot to understand how entities (People, Companies, Events) are interconnected.
- **🎯 Semantic Precision**: Uses advanced vector embeddings to understand the true intent behind your questions.
- **🛡️ Enterprise Guardrails**: Sophisticated security layers prevent prompt injection and ensure factual accuracy.
- **⚡ High-Speed Ingestion**: Support for PDFs, Markdown, Word, CSV, and HTML with instantaneous "Dual Ingestion" for pre-mapped data.

## 🏗️ The SoftMania Architecture

SoftMania operates on a **Hybrid Intelligence Loop**:

1.  **Decomposition**: Complex queries are automatically broken down into simpler logical steps.
2.  **Hybrid Retrieval**: Knowledge is pulled concurrently from both a **Semantic Vector Store (Neon)** and a **Knowledge Graph (Neo4j)**.
3.  **Synthesis & Validation**: Context is compressed and evaluated for sufficiency before a final, cited answer is generated.

## 🚀 Getting Started

### 1. Prerequisites
- **Mistral AI API Key**
- **Neon PostgreSQL** (with `pgvector` extension)
- **Neo4j Database** (Aura or Local)

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/SoftMania/chatbot.git
cd chatbot
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file with your credentials:
```env
MISTRAL_API_KEY=your_key
NEON_DATABASE_URL=your_postgres_url
NEO4J_URI=your_neo4j_uri
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

### 4. Running the Bot
```bash
python main.py
```
The API will be available at `http://localhost:7860`.

## 🛠️ API Reference

- `POST /ingest`: Upload and process documents into the intelligence core.
- `POST /query`: Send questions and receive deep-reasoned answers.
- `POST /ingest-dual`: Fast-track ingestion for pre-computed knowledge maps.
- `DELETE /clear`: Purge the intelligence core for a fresh start.

---
*Driven by the SoftMania Intelligence Engine.*
