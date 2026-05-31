# ForensIQ — AI Forensic Analyst

An LLM-powered forensic text analysis agent that assists investigators in processing unstructured case documents — suspect statements, witness testimonies, interrogation transcripts, and incident reports — to surface contradictions, construct timelines, profile entities, and generate investigative leads.

---

## Team

| Member     | Role                        |
|------------|-----------------------------|
| Muhammad Faizan Anwar  | Researcher (Architecture & Backend)      |
| Muhammad Shoaib        | Prompt Engineering & Testing|
| Muhammad Burhan Abrar  | UI Development & Integration|

**Team Name:** ForensIQ Team 
**Course:** Artificial Intelligence 
**Instructor:** Dr. Kanwal Yousaf  
**Institution:** University of Engineering and Technology, Taxila  
**Assignment:** Semester Project 

---

## Features

ForensIQ accepts raw case text (pasted or uploaded as `.txt`, `.pdf`, `.docx` files) and routes it through four analytical modules powered by an LLM inference engine:

### Core Analytical Modules

| Module               | Tab Name              | Description                                                                                      |
|----------------------|-----------------------|--------------------------------------------------------------------------------------------------|
| Contradiction Detector | Conflict Analysis     | Cross-references all statements in case memory and flags logical inconsistencies between accounts. |
| Timeline Constructor   | Event Timeline        | Extracts every time-referenced event and assembles a unified chronological sequence.               |
| Suspect Profiler       | Entity Profiles       | Aggregates information per individual — motives, behavioral flags, key statements, associations.   |
| Next-Question Generator| Investigative Leads   | Identifies information gaps and suggests targeted follow-up interrogation questions by priority.    |

### Additional Capabilities

- **Workspace Chat** — Free-form conversational interface for ad-hoc questions about loaded case documents.
- **File Upload Support** — Parse and ingest `.txt`, `.pdf`, and `.docx` files directly through the sidebar.
- **Session Memory** — All documents are held in an in-memory Python store, enabling cross-document analysis within a single session.
- **JSON Export** — Every analysis output can be downloaded as a structured JSON file for external use.

---

## Architecture

ForensIQ follows the **User Input → Prompt Template → LLM → Structured Output** pipeline specified in the project guidelines.

```
<img width="2528" height="1682" alt="Gemini_Generated_Image_2njxb32njxb32njx" src="https://github.com/user-attachments/assets/7f7e0154-9933-4ab5-8779-9e894d32489b" />

```

### Module Breakdown

| File              | Responsibility                                                                 |
|-------------------|--------------------------------------------------------------------------------|
| `config.py`       | Loads `.env`, validates API keys, exposes an immutable `Settings` dataclass.    |
| `prompts.py`      | Six prompt templates — four analytical modules, one system prompt, one chat prompt. Each enforces strict JSON output. |
| `agent.py`        | `ForensIQAgent` class — Groq SDK client, case memory management, four analysis methods, multi-turn chat, JSON parsing with markdown-fence stripping. |
| `app.py`          | Streamlit dashboard — sidebar for document ingestion, five tabbed views, session state management, download buttons. |
| `utils.py`        | File parsing utilities for `.txt`, `.pdf`, and `.docx` uploads.                |
| `styles.css`      | Minimal custom CSS theme — Inter font, soft neutral palette, card components.  |

---

## Prerequisites

- Python 3.10 or higher
- A Groq API key (free tier) — obtain one at [console.groq.com](https://console.groq.com)
- Git

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/FaizanAnwar01/ForensIQ.git
cd ForensIQ
```

### 2. Create a Virtual Environment (recommended)

```bash 
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Environment

Copy the example environment file and add your Groq API key:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_actual_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

> **Note:** The `.env` file is excluded from version control via `.gitignore`. Never commit API keys to the repository.

### 5. Launch the Application

```bash
python -m streamlit run app.py
```

The dashboard will open in your default browser at `http://localhost:8501`.

---

## Usage

### Adding Case Documents

1. Open the **sidebar** on the left.
2. Enter a descriptive label (e.g., `Suspect A — Interview 1`).
3. Either **paste** raw text into the text area, or **upload** a `.txt` / `.pdf` / `.docx` file.
4. Click **Add to case**. The document will appear under **Memory** in the sidebar.
5. Repeat for additional documents — the agent cross-references all loaded material.

### Running Analysis

Navigate to any of the five tabs in the main dashboard:

| Tab                  | Action                                                                 |
|----------------------|------------------------------------------------------------------------|
| **Conflict Analysis**    | Click "Analyse for conflicts" to cross-reference statements.       |
| **Event Timeline**       | Click "Build timeline" to extract and sort temporal events.        |
| **Entity Profiles**      | Click "Generate profiles" to build per-person profile cards.       |
| **Investigative Leads**  | Click "Generate leads" to surface gaps and follow-up questions.    |
| **Workspace Chat**       | Type questions in the chat input to query the case conversationally.|

### Downloading Results

Each analysis tab includes a **Download as JSON** button that exports the structured output for external use or reporting.

---

## Project Structure

```
ForensIQ/
├── .env.example        # Environment template (safe to commit)
├── .env                # Your API credentials (git-ignored)
├── .gitignore          # Excludes .env, __pycache__, venv
├── __init__.py         # Package metadata
├── config.py           # Configuration & API key management
├── prompts.py          # LLM prompt templates (4 modules + system)
├── agent.py            # Core agent logic & Groq SDK integration
├── app.py              # Streamlit dashboard UI
├── utils.py            # File parsing utilities (TXT, PDF, DOCX)
├── styles.css          # Custom CSS theme
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## Built With

| Technology     | Purpose                                      |
|----------------|----------------------------------------------|
| Python 3.10+   | Core language                                |
| Streamlit      | Interactive web dashboard                    |
| Groq API       | LLM inference engine (Llama 3.3 70B)        |
| Pandas         | Data formatting for timeline tables          |
| PyPDF2         | PDF text extraction                          |
| python-docx    | DOCX text extraction                         |
| python-dotenv  | Secure environment variable management       |

---

## References

1. Kim, K.J., Lee, C.H., Bae, S.E., Choi, J.H., & Kang, W. (2025). Digital forensics in law enforcement: A case study of LLM-driven evidence analysis. *Forensic Science International: Digital Investigation*, 54, 301939.
2. Xi, Z., Chen, W., Guo, X., et al. (2023). The Rise and Potential of Large Language Model Based Agents: A Survey. *arXiv:2309.07864*.
3. Xu, W., Luo, G., Meng, W., et al. (2025). MRAgent: An LLM-based automated agent for causal knowledge discovery in disease via Mendelian randomization. *Briefings in Bioinformatics*, 26(2), bbaf140.
4. Scanlon, M., Breitinger, F., Hargreaves, C., Hilgert, J.N., & Sheppard, J. (2023). ChatGPT for digital forensic investigation. *Forensic Science International: Digital Investigation*, 46, 301609.
5. Oh, D.B., Kim, D., & Kim, H.K. (2024). volGPT: Evaluation on triaging ransomware process in memory forensics with large language model. *Forensic Science International: Digital Investigation*, 49, 301756.

---

## License

This project was developed for academic purposes as part of the AI course at UET Taxila. It is not intended for production deployment in active law enforcement operations without appropriate validation, oversight, and authorization.
