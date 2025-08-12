# Agentic Video QA System

A streamlined AI pipeline for analyzing preschool video recordings. Ask a question, optionally identify your child, and receive a concise, parent-friendly answer.

## Project Structure
```
config/               # Video metadata (videos.yaml)
prompts/              # Prompt templates (*.txt)
src/                  # Core source code (graph, nodes, adapters, CLI)
tests/                # Unit tests for nodes and flow
README.md             # Project overview and instructions
requirements.txt      # Dependency specifications
```

## Setup
1. Create & activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Google Cloud project:
   ```bash
   export GOOGLE_CLOUD_PROJECT="<your-project-id>"
   ```
4. Configure video catalog in `config/videos.yaml`:
   - Open the file, remove or update the sample entries, and add your own video metadata.

## Usage
### CLI Mode
Ask a question via the command line:
```bash
python main.py --question "Did my child participate in the water activity?"
```
The system will prompt for child identification if needed, then return a final answer.

## Testing
Run test scripts:
```bash
python tests/test_child_identification.py
python tests/test_system_flow.py
python tests/test_cli_fix.py
python tests/test_vertex_ai.py
```
