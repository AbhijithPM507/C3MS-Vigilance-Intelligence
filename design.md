# C3MS Vigilance Intelligence Design

## Overview
`C3MS-Vigilance-Intelligence` is an AI-driven anti-corruption complaint intake and monitoring platform. It combines a Telegram-based complaint submission interface, multi-modal preprocessing, NLP-based PII redaction, blockchain-style integrity hashing, vector search for legal context, agentic AI workflow orchestration, and a Streamlit monitoring dashboard.

The system is implemented as a modular Python application with separate responsibilities for interface, backend logic, preprocessing, data handling, vector retrieval, and storage.

## High-Level Architecture

The system is organized into the following logical layers:

- `interface_layer/`: Telegram bot webhook ingestion and public FastAPI endpoints.
- `preprocessing/`: Multi-modal media text extraction from text, image, PDF, and audio.
- `backend/logic/`: Complaint processing orchestration through a LangGraph state graph and LLM wrappers.
- `data_layer/`: Privacy redaction, integrity hashing, vector retrieval, and persistent storage.
- `dashboard/`: Streamlit-based analytics and monitoring UI.

### Data Flow Summary

1. User submits a complaint via Telegram: text, image, PDF, or voice.
2. `interface_layer/app.py` receives and validates the input.
3. Preprocessing extracts text from media using `preprocessing/media_pipeline.py`.
4. `backend/logic/service.py` invokes data processing and then AI workflow logic.
5. `data_layer/processor.py` redacts PII, generates integrity hashes, and retrieves legal context.
6. The LangGraph workflow classifies the complaint, retrieves additional context, assesses risk, and optionally escalates.
7. Results are saved to SQLite via `data_layer/storage/database.py`.
8. High-risk cases trigger an admin Telegram alert if `ADMIN_CHAT_ID` is configured.
9. The Streamlit dashboard fetches complaint records from `/complaints` and presents KPIs and trends.

## Interface Layer

### `interface_layer/app.py`

This module provides:

- FastAPI application instance `app`.
- Telegram bot integration using `python-telegram-bot`.
- A conversation workflow for complaint format selection and submission.
- A `/webhook` endpoint for receiving Telegram updates.
- A `/complaints` endpoint for dashboard consumption.

#### Telegram workflow

- `/start` sends the user a format selection menu: `Text`, `Image`, `PDF`, or `Voice`.
- `choose_format()` stores the selected format in `context.user_data` and asks for input.
- `handle_input()` processes the user submission based on format:
  - Text is taken directly from `update.message.text`.
  - Image files are downloaded and OCR'd.
  - PDFs are downloaded and text is extracted.
  - Voice files are downloaded and transcribed.
- After extraction, it validates minimum length and calls `process_complaint()`.
- Saves the processed complaint to the database.
- Sends an admin alert when risk is `High`.
- Responds to the user with complaint metadata and integrity status.

#### Complaint retrieval

- `track_command()` supports `/track <complaint_id>` to return complaint status.
- The `/complaints` endpoint returns all complaint records from SQLite for dashboard use.

## Preprocessing Layer

### `preprocessing/media_pipeline.py`

This module dispatches media processing based on file extension:

- `.jpg`, `.jpeg`, `.png` → `extract_text_from_image()`
- `.pdf` → `extract_text_from_pdf()`
- `.mp3`, `.wav`, `.m4a`, `.ogg` → `transcribe_audio()`

### `preprocessing/image_extractor.py`

The image extractor implements a hybrid OCR pipeline:

- Uses OpenCV to convert images to grayscale and adaptive thresholding.
- Uses Tesseract for printed text extraction.
- Falls back to EasyOCR for handwriting or low-confidence text.

### `preprocessing/pdf_extractor.py`

PDF extraction uses a two-stage approach:

- Attempts direct text extraction with `PyPDF2`.
- If that fails, converts pages to images and reuses the image OCR pipeline.

### `preprocessing/audio_transcriber.py`

Audio transcription uses `faster-whisper`:

- Converts input audio to 16 kHz, mono WAV via `ffmpeg`.
- Loads a CPU-optimized Whisper model (`large-v2` with int8 inference).
- Transcribes audio segments into plain text.

## Backend Logic

### `backend/logic/service.py`

This is the core request orchestrator:

- Generates a UUID for each complaint.
- Calls `data_layer.processor.process_complaint()` first.
- Builds a LangGraph workflow and invokes it with redacted text and legal context.
- Merges blockchain metadata into the final result.

### `backend/logic/graph_builder.py`

The LangGraph workflow is defined with four nodes:

- `categorize`
- `retrieve`
- `analyze`
- `escalate`

Edges:

- `categorize` → `retrieve`
- `retrieve` → `analyze`
- `analyze` → `escalate` or end depending on `escalation_required`
- `escalate` → end

The graph uses `ComplaintState` typed schema.

### `backend/logic/state_schema.py`

Defines the expected state keys used across the workflow:

- `complaint_text`
- `category`
- `severity_score`
- `retrieved_docs`
- `risk_level`
- `recommended_action`
- `relevant_laws`
- `escalation_required`
- `structured_output`

### `backend/logic/llm_wrapper.py`

Encapsulates the LLM call to an Ollama endpoint:

- Sends prompt text to `http://localhost:11434/api/generate`
- Requests model `llama3`
- Handles network and response errors

## Graph Nodes

### `backend/logic/nodes/categorizer_node.py`

Responsibilities:

- Optionally extracts structured fields `Official Name` and `Place` using regex.
- Applies selective PII redaction while preserving protected values.
- Builds a prompt for category classification and severity scoring.
- Calls `generate_response()` and parses JSON from the LLM output.
- Sets default fallback values when LLM output is missing or invalid.

### `backend/logic/nodes/retrieval_node.py`

Responsibilities:

- Performs semantic search on the legal vector store.
- Uses `query_legal_context()` with the complaint text.
- Stores retrieved documents in `state["retrieved_docs"]`.

### `backend/logic/nodes/risk_analysis_node.py`

Responsibilities:

- Builds a prompt combining complaint text, category, and retrieved legal context.
- Asks the LLM to output risk level, recommended action, and relevant laws.
- Parses JSON from the LLM result.
- Determines `escalation_required` based on `severity_score > 0.8`.

### `backend/logic/nodes/escalation_node.py`

Responsibilities:

- Appends an escalation directive to the existing recommended action.
- The node is executed only when the workflow condition evaluates to escalate.

## Data Layer

### `data_layer/processor.py`

This module bridges privacy, integrity, and retrieval:

1. Redacts sensitive PII using `data_layer.pii_redactor.redactor.redact_pii()`.
2. Generates a blockchain-style integrity block via `data_layer.blockchain.process_integrity.process_integrity()`.
3. Retrieves legal context through `data_layer.vector_db.query.query_legal_context()`.
4. Returns a structured payload with redacted text, hash metadata, timestamp, and legal context.

### PII Redaction: `data_layer/pii_redactor/redactor.py`

The redaction layer uses several techniques:

- Regex-based masking for phone numbers, email addresses, and Aadhaar numbers.
- spaCy named entity recognition to redact `PERSON` entities.
- Preserves manually protected entities passed into the function.
- Leaves `GPE` and `LOC` intact to retain governance-critical location data.

### Blockchain Integrity: `data_layer/blockchain`

The integrity submodule includes:

- `hash_chain.py`
  - Creates SHA-256 hashes from complaint ID, redacted text, previous hash, and timestamp.
  - Supports chain verification by validating linkages and recalculating hashes.
- `process_integrity.py`
  - Orchestrates block creation and optional anchoring.
  - Anchors the hash every `anchor_every` blocks.
- `anchor.py`
  - Writes anchor records to `data_layer/blockchain/anchor_log.json`.

The output block includes:

- `data_hash`
- `previous_hash`
- `timestamp`
- `complaint_id`

### Vector Retrieval: `data_layer/vector_db`

Key responsibilities:

- `pinecone_client.py` configures Pinecone using environment variables.
- `query.py` encodes complaint text with `SentenceTransformer("all-MiniLM-L6-v2")` and queries the Pinecone index.
- `indexer.py` upserts chunk embeddings into Pinecone for index creation.
- `document_loader.py` reads PDF text.
- `chunker.py` slices legal documents into 500-character chunks.
- `setup_legal_index.py` is a utility to bootstrap the legal index from a PDF file.

### Persistent Storage: `data_layer/storage/database.py`

This module uses SQLite to store complaint records in `complaints.db`.

Stored fields:

- `id`
- `official_name`
- `position`
- `place`
- `description`
- `category`
- `risk_level`
- `severity_score`
- `timestamp`
- `integrity_hash`
- `evidence_hash`
- `escalation_required`
- `escalation_timestamp`
- `status`

The module provides:

- `init_db()` to create the table if needed.
- `save_complaint()` to insert complaint metadata.
- `get_complaint_by_id()` for complaint lookup.

## Dashboard

### `dashboard/app.py`

The Streamlit dashboard provides live monitoring and analytics:

- Requests complaint data from `http://localhost:8000/complaints`.
- Shows KPIs: total complaints, high-risk cases, and average severity score.
- Displays a recent complaints feed and escalation summary.
- Renders category breakdown and position distribution charts using Plotly.
- Shows daily complaint trends and highest severity case details.
- Uses `st.cache_data(ttl=10)` to refresh data regularly.
- Triggers a rerun after a 10-second sleep, providing near-live refresh behavior.

## External Dependencies and Deployment Assumptions

### Required infrastructure

- `python-telegram-bot` webhook support for Telegram message ingestion.
- `FastAPI` and `uvicorn` to run the backend API.
- `Streamlit` for the dashboard.
- `pinecone-client` for vector index querying.
- `Ollama` running locally on `http://localhost:11434` with model `llama3`.
- `spaCy` with `en_core_web_sm` installed.
- `ffmpeg` available for audio preprocessing.
- `Tesseract OCR` available at `C:\Program Files\Tesseract-OCR\tesseract.exe`.

### Environment configuration

The project expects these environment variables:

- `TELEGRAM_BOT_TOKEN`
- `ADMIN_CHAT_ID`
- `PINECONE_API_KEY`
- `PINECONE_INDEX`

### Deployment notes

- `interface_layer/app.py` initializes the database and an `uploads` directory on startup.
- The Telegram bot webhook endpoint is `POST /webhook` and must be set in Telegram Bot settings.
- The dashboard depends on the backend `/complaints` endpoint and therefore requires the API to be running.
- The blockchain integrity chain is incremental in design, but the existing implementation uses a mocked static `previous_hash = "0"` and `total_blocks = 1` at complaint creation.

## Behavioral Summary

### Complaint lifecycle

1. User starts a conversation and chooses input format.
2. Input is received, downloaded, and extracted into plain text.
3. Basic validation ensures the text is sufficiently detailed.
4. Complaint processing begins with PII redaction and integrity hashing.
5. Legal context is fetched from a Pinecone vector store via semantic search.
6. The AI workflow classifies the complaint and computes severity.
7. Risk analysis uses retrieved legal context and issues escalation recommendations.
8. High-risk complaints can trigger administrator notifications.
9. Complaint metadata is persisted and exposed to the dashboard.

### Security and privacy

- Sensitive personal identifiers are masked before analysis.
- Location data remains available because it is needed for governance context.
- A hash chain records complaint integrity, supporting tamper detection if the chain is verified externally.

## Key Observations

- The codebase is architected around separation of concerns: ingestion, preprocessing, privacy, AI logic, retrieval, and storage.
- The LangGraph workflow abstracts decision-making into composable nodes.
- The actual escalation and blockchain anchoring mechanisms are currently light; the architecture is present but could be extended to full multi-block chain operations.
- The dashboard provides direct read-only analytics and does not write back to the backend.

## Files of primary importance

- `README.md`
- `interface_layer/app.py`
- `backend/logic/service.py`
- `backend/logic/graph_builder.py`
- `backend/logic/nodes/*.py`
- `data_layer/processor.py`
- `data_layer/pii_redactor/redactor.py`
- `data_layer/blockchain/*.py`
- `data_layer/vector_db/*.py`
- `data_layer/storage/database.py`
- `preprocessing/*.py`
- `dashboard/app.py`

## Conclusion

The system is designed as a modular platform that combines Telegram-based intake, media preprocessing, privacy-safe AI reasoning, legal context retrieval, integrity tracking, and operational monitoring. The current implementation wires these layers together for complaint submission, analysis, and persistence while leaving room for a stronger blockchain chain implementation and more advanced escalation automation.