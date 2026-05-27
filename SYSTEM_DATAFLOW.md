# C3MS Vigilance Intelligence - System Dataflow and Architecture

## 1. Overview
This repository implements an AI-driven anti-corruption complaint intake and analysis platform. It accepts complaint submissions via Telegram in multiple formats, preprocesses the media, redacts sensitive information, stores records securely, enriches complaints with legal context using vector search, processes them through an LLM-driven workflow, and exposes data for a Streamlit monitoring dashboard.

## 2. High-Level Layered Architecture

### 2.1 Interface Layer
- `interface_layer/app.py`
- Provides a FastAPI app and Telegram webhook endpoint.
- Receives complaint submissions via Telegram and tracks user conversations.
- Stores pending complaints in the database and enqueues background processing tasks.
- Exposes `/complaints` for dashboard consumption.

### 2.2 Preprocessing Layer
- `preprocessing/media_pipeline.py`
- Normalizes multi-modal inputs: text, images, PDFs, and audio.
- Image extraction: `preprocessing/image_extractor.py`
- PDF extraction: `preprocessing/pdf_extractor.py`
- Audio transcription: `preprocessing/audio_transcriber.py`

### 2.3 Backend Logic Layer
- `backend/logic/service.py`
- `backend/logic/graph_builder.py`
- `backend/logic/llm_wrapper.py`
- `backend/logic/nodes/*`
- Orchestrates complaint processing through a state graph built with LangGraph.
- Calls the data processor first, then executes the AI workflow.

### 2.4 Data Layer
- `data_layer/processor.py`
- `data_layer/pii_redactor/redactor.py`
- `data_layer/blockchain/*`
- `data_layer/vector_db/*`
- `data_layer/storage/database.py`
- Handles PII redaction, integrity hashing, legal context retrieval, and persistent storage.

### 2.5 Dashboard
- `dashboard/app.py`
- Streamlit app that consumes complaint records and displays KPIs, trends, and escalations.

## 3. End-to-End Dataflow

### 3.1 Submission Intake
1. User sends `/start` to the Telegram bot.
2. Bot asks for input format: `Text`, `Image`, `PDF`, or `Voice`.
3. User submits complaint text or uploads media.
4. `interface_layer/app.py` saves a pending complaint record and enqueues `process_complaint_task`.

### 3.2 Background Task Execution
1. `backend/tasks.py` loads the pending complaint from the database.
2. If the input is not text, it uses `preprocessing/media_pipeline.extract_text_from_media` to extract text.
3. Validates extracted text length.
4. Calls `backend.logic.service.process_complaint`.

### 3.3 Data Processing Pipeline
1. `backend/logic/service.process_complaint` creates a new complaint UUID.
2. Retrieves the latest chain hash from the database using `data_layer.storage.database.get_latest_hash()`.
3. Calls `data_layer.processor.process_complaint` with complaint text and previous hash.

#### 3.3.1 PII Redaction
- Uses `data_layer.pii_redactor.redactor.redact_pii`.
- Removes phone numbers, emails, Aadhaar numbers using regex.
- Uses spaCy named entities to redact persons.
- Preserves protected official entities if provided.

#### 3.3.2 Blockchain-style Integrity
- `data_layer.blockchain.process_integrity.process_integrity` creates an integrity block.
- `data_layer.blockchain.hash_chain.create_block` computes SHA-256 over complaint ID, redacted text, previous hash, and timestamp.
- Optionally anchors every N blocks to `data_layer/blockchain/anchor_log.json`.

#### 3.3.3 Legal Context Retrieval
- `data_layer.vector_db.query.query_legal_context` encodes the complaint text with `SentenceTransformer('all-MiniLM-L6-v2')`.
- Queries Pinecone index configured in `data_layer/vector_db/pinecone_client.py`.
- Returns top matching legal text chunks.

### 3.4 AI Workflow
1. `backend.logic.service` builds a LangGraph workflow from `backend.logic.graph_builder.build_graph()`.
2. Workflow nodes:
   - `categorize` (`backend.logic.nodes.categorizer_node.categorize_node`)
   - `retrieve` (`backend.logic.nodes.retrieval_node.retrieval_node`)
   - `analyze` (`backend.logic.nodes.risk_analysis_node.risk_analysis_node`)
   - `escalate` (`backend.logic.nodes.escalation_node.escalation_node`)
3. The workflow is executed with state containing redacted complaint text and retrieved docs.

#### 3.4.1 Categorization Node
- Redacts PII again, with protected official entity preservation.
- Extracts category and severity score from the LLM.
- Category options: `Bribery`, `Service Delay`, `Favoritism`, `Fraud`, `Other`.

#### 3.4.2 Retrieval Node
- Performs vector search over legal documents and attaches retrieved legal context to state.

#### 3.4.3 Risk Analysis Node
- Builds a prompt containing complaint text, category, and legal context.
- Uses the LLM to determine risk level, recommended action, and relevant laws.
- Sets `escalation_required` if `severity_score > 0.8`.

#### 3.4.4 Escalation Node
- If triggered, appends a direct escalation recommendation to the action text.

### 3.5 Finalization and Notification
1. The final result includes complaint metadata plus blockchain integrity values.
2. `backend/tasks.py` updates the complaint record with category, risk, severity, status, and hash chain values.
3. If risk is `High` and `ADMIN_CHAT_ID` exists, sends an admin Telegram alert.
4. Replies to the user with complaint completion details.

## 4. Deployment and Runtime Behavior

### 4.1 Required Runtime Services
- PostgreSQL database configured via `DATABASE_URL`.
- Pinecone vector index configured via `PINECONE_API_KEY` and `PINECONE_INDEX`.
- Redis for Celery broker/ backend (configured via `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`).
- Ollama LLM service available at `http://localhost:11434/api/generate`.
- Tesseract OCR installed on Windows at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- `ffmpeg` available on the PATH for audio conversion.

### 4.2 Main Processes
- `uvicorn interface_layer.app:app --reload` for the API and Telegram webhook.
- `celery -A backend.celery_app worker --loglevel=info` for background complaint processing.
- `streamlit run dashboard/app.py` for live monitoring.

## 5. Important File Locations
- `interface_layer/app.py`: Telegram and FastAPI interface, webhook, complaint submission.
- `backend/tasks.py`: Celery task, complaint ingestion, notification.
- `backend/logic/service.py`: Top-level complaint processing orchestration.
- `backend/logic/graph_builder.py`: LangGraph workflow definition.
- `backend/logic/nodes/*.py`: AI workflow node implementations.
- `data_layer/processor.py`: Redaction, integrity, and retrieval pipeline.
- `data_layer/pii_redactor/redactor.py`: PII detection and redaction rules.
- `data_layer/blockchain/*`: Integrity and anchor storage.
- `data_layer/vector_db/*`: Pinecone vector search and index setup.
- `data_layer/storage/database.py`: PostgreSQL complaint storage and hash chain state.
- `preprocessing/*`: Media normalization and extraction.
- `dashboard/app.py`: Streamlit dashboard consuming `/complaints`.

## 6. Observations and Notes
- The system is built to process multi-modal complaint input within a single workflow.
- It uses a combination of local AI inference, vector retrieval, structured workflow graphing, and blockchain-style verification.
- The database code currently mixes PostgreSQL and SQLite patterns, but runtime expects PostgreSQL via `DATABASE_URL`.
- The dashboard polls `http://localhost:8000/complaints`, so the API must run on port 8000.

## 7. How the Data Moves
1. Telegram `webhook` → `interface_layer/app.py` → pending DB row.
2. Celery `process_complaint_task` → media extraction if needed.
3. `backend.logic.service` → `data_layer.processor`:
   - Redact text
   - Hash data
   - Lookup legal context
4. LangGraph workflow classifies and analyzes.
5. Result saved back to DB and user notified.
6. Dashboard reads DB data through `/complaints`.

---

This document reflects the current codebase and execution flow as implemented in the workspace on May 27, 2026.