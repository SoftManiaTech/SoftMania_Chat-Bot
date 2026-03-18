# Application Data Flow (User Experience)

This simple diagram explains how the SoftMania Chat-Bot works behind the scenes when you talk to it or upload documents. It breaks down the highly technical layers into an easy-to-understand process flow.

```mermaid
flowchart TD
    %% Define Visual Styles
    classDef userUI fill:#2563eb,color:#fff,stroke-width:2px,stroke:#1d4ed8
    classDef security fill:#059669,color:#fff,stroke-width:2px,stroke:#047857
    classDef process fill:#475569,color:#fff,stroke-width:2px,stroke:#334155
    classDef memory fill:#d97706,color:#fff,stroke-width:2px,stroke:#b45309
    classDef brain fill:#7c3aed,color:#fff,stroke-width:2px,stroke:#6d28d9

    subgraph 1. The User Experience (What You See)
        Upload[Upload a File\nThrough the Portal]:::userUI
        Chat[Type a Question\nIn the Chat Widget]:::userUI
        Read[Read the AI Answer\nIn the Chat Widget]:::userUI
    end

    subgraph 2. The Verification Gate
        Check{Verify Session Identity\nand Secure Connections}:::security
    end

    subgraph 3. Reading and Searching (The Librarians)
        BreakDown(Break document into\nbite-sized paragraphs):::process
        Search(Find exact matching\nparagraphs and topics):::process
    end

    subgraph 4. The Brain (Artificial Intelligence)
        Understand(AI reads paragraphs and\nfinds connected concepts):::brain
        Answer(AI reads everything found\nand writes a helpful human response):::brain
    end

    subgraph 5. The Long-Term Memory
        Database[(Company Memory\nThe Databases)]:::memory
    end

    %% Teaching the AI (Ingestion Flow)
    Upload == "1. File Uploaded" ==> BreakDown
    BreakDown == "2. Safely organized text" ==> Database
    BreakDown -. "3. Pass hard topics to AI" .-> Understand
    Understand -. "4. AI saves connected ideas" .-> Database

    %% Asking the AI (Query Flow)
    Chat == "A. Sends Question" ==> Check
    Check == "B. Connection is Safe" ==> Search
    Search == "C. Looks up best matches" ==> Database
    Database == "D. Returns factual memory" ==> Answer
    Answer == "E. AI summarizes findings" ==> Read
```

### Flow 1: Teaching the Chat-Bot (Uploading Files)
When you upload a file using the API portal:
1. **Breaking it down:** The system splits large files into small, organized paragraphs so it takes up less memory.
2. **Finding the meaning:** It feeds these paragraphs to an AI model to detect the underlying concepts and relationships.
3. **Saving it for later:** Both the raw paragraphs and the extracted relationships are stored in the **Long-Term Memory** databases securely.

### Flow 2: Talking to the Chat-Bot (Asking Questions)
When you type a question into the widget:
1. **Security First:** The system ensures you are who you say you are using secure cookies—meaning your chat remains private.
2. **Fact Searching:** Our search engine goes into the databases and retrieves specifically what you're asking about, ignoring the rest.
3. **The Answer:** By looking at the verified facts returned from memory, the AI constructs a perfectly accurate, conversational answer and sends it right back to your chat window.
