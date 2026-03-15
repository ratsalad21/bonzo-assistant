# Bonzo Assistant

Bonzo Assistant is a small Streamlit chat app built for learning.

It lets you explore:

- a simple Python web app
- chat with an LLM-style interface
- saved chat sessions
- uploaded documents
- a bundled sample document for your first RAG test
- optional RAG (retrieval-augmented generation)
- basic multi-agent orchestration ideas

You can run it in two modes:

- `MOCK_MODE=true`
  - no paid API calls
  - best for learning the app structure
- `MOCK_MODE=false`
  - uses the real OpenAI API
  - requires an API key and billing/quota

## If You Are Totally New

If you have never built a Python app before, that is okay.

You do not need to understand every file before you begin.

For your first run, the goal is simply:

1. install the app
2. turn on mock mode
3. run it
4. open it in the browser

Once that works, you can learn the deeper ideas one at a time.

## What This App Is

This repo is a beginner-friendly learning project.

It is not trying to be a full production assistant platform. It is trying to show, in a small codebase, how these ideas fit together:

- `Streamlit` gives us the web UI
- `OpenAI` can generate responses
- `Chroma` stores document embeddings for search
- local JSON files store chat history
- local files in `docs/` store uploaded documents
- a simple orchestrator chooses whether specialist agents should help on a turn

## What You Can Learn Here

This app is useful if you want to understand:

- how a Python UI app is structured
- how chat messages move through an app
- how environment variables work
- what RAG means in practice
- how a simple agent orchestrator can call specialist roles
- how local persistence works

## Beginner Summary

If you are brand new, here is the shortest explanation:

1. You run the app with `streamlit run app.py`.
2. The app opens in your browser.
3. You type a message.
4. The app decides whether to answer directly or use a specialist.
5. The response appears in the chat.
6. Your chat history is saved locally on disk.

If you turn on document search:

1. You upload a document.
2. The app breaks it into chunks.
3. The chunks are stored in a local Chroma database.
4. Later, the app can search those chunks to help answer questions.

The app also includes a bundled sample file named `sample-deploy-note.md` so you can try RAG without finding your own document first.

## Plain-English Glossary

Here are the main words used in this repo in very simple language.

### Python

The programming language used to build this app.

### Streamlit

A tool that lets Python code create a simple website-like app.

### API

A way for one program to talk to another.

### LLM

An AI model that can read text and write text.

### Mock mode

A practice mode.

The app still runs, but it does not make paid OpenAI requests.

### RAG

Short for retrieval-augmented generation.

In plain English, it means:

- search the uploaded files
- find the useful parts
- use those parts while answering

### Embeddings

A way to represent text as numbers so the app can compare meaning.

You do not need to understand the math to use this app.

### Chroma

The small local database this app uses for document search.

### Agent

In this app, an agent is just a specialist role inside the same program.

It is not a separate website or service.

## Project Layout

These are the most important files:

- `app.py`
  - the Streamlit entry point
- `app_state.py`
  - sets up Streamlit session state
- `sidebar.py`
  - renders the left sidebar and collects settings
- `ui.py`
  - shared UI rendering and custom styling
- `chat_flow.py`
  - handles one full chat turn
- `llm.py`
  - builds instructions and streams responses
- `agents.py`
  - simple orchestrator plus specialist routing
- `agent_tools.py`
  - helper functions the agents can use
- `rag.py`
  - Chroma indexing and retrieval logic
- `documents.py`
  - upload, extract, preview, and manage files
- `sessions.py`
  - save and load chat history
- `config.py`
  - environment variables and app settings
- `.env.example`
  - sample environment file

These folders hold runtime data:

- `docs/`
  - uploaded source files and the bundled sample document
- `chat_history/`
  - saved chat sessions as JSON
- `chroma_db/`
  - local vector database files

## Requirements

You need:

- Python 3.12 or newer
- PowerShell or another terminal
- a browser

You do not need an OpenAI API key if you use mock mode.

## First-Time Setup

Open a terminal in `G:\bonzo-assistant`.

If the commands below feel unfamiliar, that is normal.

For now, treat them like a checklist.

### 1. Create a virtual environment

A virtual environment keeps this project's Python packages separate from other projects on your computer.

PowerShell:

```powershell
python -m venv .venv
```

If `python` is not on your PATH, use your full Python path instead:

```powershell
& "C:\Users\matte\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
```

### 2. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

When this works, your terminal usually shows something like `(.venv)` at the start of the line.

If PowerShell blocks the script, you may need to allow local scripts for your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

This downloads the Python packages the app needs.

### 4. Create your local environment file

```powershell
Copy-Item .env.example .env
```

Think of `.env` as this app's local settings file.

### 5. Pick your mode

For beginners, start with mock mode.

In `.env`:

```env
MOCK_MODE=true
```

If you want to use the real OpenAI API later:

```env
MOCK_MODE=false
OPENAI_API_KEY=your_key_here
```

Leave `OPENAI_BASE_URL` empty unless you are intentionally using a different OpenAI-compatible endpoint.

### 6. Run the app

```powershell
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

When the app opens for the first time, you should see:

- a welcome panel
- a few starter prompt buttons
- a sidebar button to index the bundled sample document

## Five-Minute Setup

If you want the shortest possible version, run these commands in order:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Then open `.env` and make sure it contains:

```env
MOCK_MODE=true
```

Then go to:

```text
http://localhost:8501
```

## The Easiest Way To Start

If you want the safest beginner path:

1. Set `MOCK_MODE=true`
2. Run the app
3. Ask a simple question
4. Start a new chat session
5. Change the system prompt
6. Click one of the starter prompts
7. Use `Index bundled sample doc` in the sidebar
8. Turn on `Use document search (RAG)` and ask what the sample note says about startup commands

That gives you a working learning loop without paying for API usage.

## Environment Variables

The main settings live in `.env`.

### `MOCK_MODE`

- `true`
  - no real OpenAI calls
  - local fake responses and fake embeddings
- `false`
  - real OpenAI calls
  - requires a working API key

### `OPENAI_API_KEY`

Your real OpenAI API key.

Only needed when `MOCK_MODE=false`.

### `OPENAI_BASE_URL`

Usually leave this blank.

Only set it if you are using another OpenAI-compatible endpoint, such as Azure OpenAI later.

### `APP_CONFIGURATION_ENDPOINT`

Optional Azure App Configuration endpoint.

When this is set, the app will try to load non-secret settings from Azure App Configuration at startup.

### `APP_CONFIGURATION_LABEL`

Optional App Configuration label.

This is useful for environment-specific values such as `dev`, `test`, or `prod`.

### `APP_CONFIGURATION_PREFIX`

Optional key prefix for App Configuration keys.

The Terraform starter uses `bonzo:` so keys like `bonzo:OPENAI_MODEL` load into the app as `OPENAI_MODEL`.

### `OPENAI_MODEL`

The chat model name.

For learning, a small model is fine.

### `EMBEDDING_MODEL`

Used when generating embeddings for RAG.

### `DOCS_DIR`

Where uploaded files are saved locally.

### `CHAT_HISTORY_DIR`

Where saved chat JSON files live.

### `CHROMA_DB_PATH`

Where the local Chroma vector database lives.

## Mock Mode Explained

Mock mode exists so you can learn the app without paying for API usage.

When mock mode is on:

- the app still runs normally
- the chat UI still works
- chat sessions still save
- uploaded documents still save
- the retrieval flow still works
- agent activity still shows up

What changes is:

- replies are generated locally instead of by OpenAI
- embeddings are generated locally instead of by OpenAI

So mock mode is not "fake app mode." It is "real app shape, fake provider."

If you do not want to pay for API usage, this is the mode you want.

## Real OpenAI Mode Explained

When `MOCK_MODE=false`:

- the app uses the OpenAI API for responses
- the app uses the OpenAI embeddings API for document indexing

This is closer to how a real hosted app would behave, but it can cost money.

If you do not want charges, stay in mock mode.

## How A Chat Turn Works

This is the basic flow for one message:

1. You type a prompt.
2. The app saves your user message into session state.
3. The orchestrator looks at the prompt.
4. It decides whether to use:
   - no specialist
   - `retrieval_agent`
   - `coding_agent`
   - `writing_agent`
   - or a sequence of them
5. Specialist outputs are turned into structured handoff notes.
6. The app builds the final instructions.
7. The response is streamed into the UI.
8. The assistant message is saved to disk.

You do not need to memorize this.

It is here so the code feels less mysterious later.

## What The Agents Mean

This app keeps one UI and one main assistant experience.

The "agents" are not separate apps. They are specialist roles inside the same Python app.

If the word "orchestration" sounds intimidating, think of it like this:

- one manager decides what kind of help is needed
- specialists do smaller focused jobs
- one final answer comes back to the user

### `orchestrator`

The top-level decision maker.

It decides:

- whether specialists are needed
- what order to run them in
- when to stop
- how to combine their outputs into one final answer

### `retrieval_agent`

Used when the prompt appears to depend on uploaded documents.

It can:

- search indexed document chunks
- preview a named document
- return a structured handoff about useful evidence

### `coding_agent`

Used for technical prompts.

It tries to make answers more concrete and implementation-focused.

### `writing_agent`

Used when the prompt asks for rewriting, polishing, summarizing, or better structure.

It helps make the final answer clearer and easier to read.

## What RAG Means In This App

RAG stands for retrieval-augmented generation.

In simple terms:

- you upload documents
- the app indexes them
- later the app searches those documents
- the retrieved text is added as context for answering

This helps when you want the assistant to answer based on your files instead of only general model knowledge.

If you want the simplest mental model, think:

- "search my uploaded notes first"
- then "answer using those notes"

## How Document Upload Works

When you upload a file:

1. the file is saved into `docs/`
2. text is extracted
3. the text is split into chunks
4. embeddings are created
5. the chunks and embeddings are saved into Chroma

Supported file types:

- `.txt`
- `.md`
- `.pdf`

## What Gets Saved On Disk

This app stores data locally.

### Chat sessions

Saved in `chat_history/` as JSON files.

That means:

- chats survive app restarts
- you can switch between old sessions
- you can inspect the files directly if you want

### Uploaded documents

Saved in `docs/`.

### Vector database

Saved in `chroma_db/`.

That is how indexed document search persists between runs.

## Beginner Tour Of The UI

### Main chat area

This is where:

- messages appear
- responses stream in
- retrieved document matches can be shown
- agent activity can be inspected

### Sidebar

This is where you can:

- see app status
- switch chat sessions
- create or delete sessions
- upload documents
- index the bundled sample document
- preview saved documents
- turn RAG on or off
- turn multi-agent orchestration on or off
- turn writing or coding specialists on or off
- change temperature and output token settings
- edit the system prompt

If you are brand new, the most important sidebar controls are:

- `Use document search (RAG)`
- `Use multi-agent orchestration`
- `Allow writing specialist`
- `Allow coding specialist`
- `System Prompt`

## Recommended Learning Order

If you want the smoothest learning path:

1. Run the app in mock mode.
2. Ask a plain question.
3. Click one of the starter prompt buttons.
4. Start a new session and switch between sessions.
5. Change the system prompt.
6. Try a writing prompt.
7. Try a coding prompt.
8. Index the bundled sample document.
9. Turn on RAG and ask a document-related question.
10. Open the agent activity panel and see what happened.

## Common Beginner Questions

### Do I need an API key?

No, not if you use `MOCK_MODE=true`.

### Is this a production app?

No. It is a learning project with useful architecture ideas.

### Are the agents separate services?

No. They are specialist roles inside the same app.

### Why use a virtual environment?

So this project's packages do not conflict with packages from other Python projects.

### Why does the app save files locally?

Because local persistence is easier to understand while learning.

### What should I ignore at first?

Ignore these until the app is already running:

- the deeper agent logic
- the retrieval math
- token budgeting details
- Azure deployment ideas

Get the app running first. Then explore one idea at a time.

## Troubleshooting

### `streamlit` is not recognized

Make sure:

- the virtual environment is activated
- dependencies were installed with `pip install -r requirements.txt`

### The browser page does not open

Try opening `http://localhost:8501` manually.

### PowerShell blocks `.venv\Scripts\Activate.ps1`

Use:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### OpenAI requests fail

Check:

- `MOCK_MODE`
- `OPENAI_API_KEY`
- available quota/billing if using real OpenAI mode

### I do not want to pay for API usage

Use this in `.env`:

```env
MOCK_MODE=true
```

That is the recommended beginner mode for this repo.

### Uploaded documents do not affect answers

Check:

- `Use document search (RAG)` is enabled
- the document was uploaded successfully
- the question actually refers to the uploaded document
- or try the bundled sample document first

## Tests

This repo now includes a few lightweight tests.

Run them with:

```powershell
pytest
```

These tests are intentionally small. They mostly check:

- agent routing
- local document listing
- session save/load behavior

## Docker

If you want a quick containerized run, this repo now includes:

- `Dockerfile`
- `.dockerignore`

Build the image:

```powershell
docker build -t bonzo-assistant .
```

Run the container:

```powershell
docker run --rm -p 8501:8501 --env-file .env bonzo-assistant
```

Then open:

```text
http://localhost:8501
```

For a beginner-friendly first container run, keep `MOCK_MODE=true`.

## Azure Note

If you later want to host this app, a simple first target is Azure App Service or Azure Container Apps.

For this learning repo, the easiest path is:

- keep it as one app
- use mock mode or a small OpenAI-backed setup
- add hosting only after the local app feels comfortable

This repo now includes a Terraform starter for Azure App Service as a Linux container in:

```text
infra/terraform/azure-app-service
```

and a separate bootstrap workspace for remote state in:

```text
infra/terraform/bootstrap-state
```

That workspace provisions:

- Azure Container Registry
- Linux App Service
- Key Vault
- App Configuration

The bootstrap workspace provisions:

- Azure Storage account for Terraform state
- blob container for remote state and locking

See the deployment notes in:

```text
infra/terraform/azure-app-service/README.md
```

GitHub Actions workflows now live in:

```text
.github/workflows
```

They cover:

- `ci.yml`
  - Python compile/tests plus Terraform formatting and validation
- `deploy-app.yml`
  - build, push, and deploy the container to Azure App Service
- `deploy-infra.yml`
  - run the App Service Terraform workspace with remote state

If you want the click-by-click Azure and GitHub setup for OIDC, secrets, variables, and role assignments, the detailed guide is in:

```text
infra/terraform/azure-app-service/README.md
```

## If You Want To Keep Going Later

Once the beginner path feels comfortable, good next steps are:

- improve mock responses
- add tests
- prepare the app for Azure deployment
- switch from mock mode to real OpenAI mode
- make the orchestration smarter

## Quick Commands

Create venv:

```powershell
python -m venv .venv
```

Activate venv:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create `.env`:

```powershell
Copy-Item .env.example .env
```

Run the app:

```powershell
streamlit run app.py
```
