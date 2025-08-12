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
4. Authenticate to Google Cloud (for Vertex AI + GCS access):
   ```bash
   gcloud auth application-default login
   ```
   - Ensure the active credentials have access to the GCS bucket objects (at least `roles/storage.objectViewer`).
   - Enable the Vertex AI and Cloud Storage APIs for your project.

5. Configure video catalog in `config/videos.yaml`:
   - Open the file, remove or update the sample entries, and add your own video metadata.
   - Each entry must include a `gcs_uri` (for example `gs://bucket/path/video.mp4`).
   - Optional fields like `session-type`, `start-time`, and `end-time` can be either numeric minutes or `HH:MM` strings.

## Usage
### CLI Mode
Ask a question via the command line:
```bash
python main.py --question "Did my child participate in the water activity?"
```
The system will prompt for child identification if needed, then return a final answer.

### One-time: Generate a Day Transcript (fast path)
We support a transcript-first path that can answer overview questions without running per-video analyzers.

Generate and cache a transcript for the current day (uses the same Vertex AI model and your catalog videos):
```bash
python -m scripts.generate_transcript
```
- The script prints the exact prompt used, asks for confirmation, analyzes all videos listed in `config/videos.yaml`, and writes `data/transcripts/transcript_YYYY-MM-DD.txt`.
- Project: Uses `GOOGLE_CLOUD_PROJECT` if set; otherwise defaults to `clever-environs-458604-c8` inside the script (adjust as needed).

## How It Works (Multimodal)
- Model: Uses Gemini 2.5 Flash on Vertex AI (`gemini-2.5-flash`) for multimodal analysis.
- Video input: Videos are provided via their GCS URIs from `config/videos.yaml`.
- Invocation: The analyzer sends both the natural-language prompt and a GCS video reference to Gemini using `vertexai.generative_models.GenerativeModel` and `Part.from_uri(...)`.
- Grounding: The analyzer prompt enforces “answer only from the video” and returns “Not enough evidence in this video.” when uncertain.

Environment defaults:
- `GOOGLE_CLOUD_PROJECT` must be set.
- Region defaults to `us-central1` (configurable in `src/adapters/llm_adapter.py`).
- Ensure your credentials can read the referenced GCS objects.

Quick validation:
```bash
python main.py --question "Did the teacher run any small-group activity after circle time?"
```
You should see logs indicating the model is called with a GCS URI, and answers referencing observable events in the video.

## Architecture
- LangGraph workflow orchestrates the end-to-end QA pipeline. The graph and nodes live in `src/graph.py` and `src/nodes/` respectively; state is `src/state.py`.

- Nodes (in order of flow):
  - `child_identifier` (async): Collects the child’s name and clothing. Sets `waiting_for_child_info=True` if missing; otherwise passes along `child_info` and the original question.
  - `video_picker`: Chooses relevant videos from the catalog for the user’s question. Outputs `target_videos` (list of IDs).
  - `question_refiner`: Refines the user’s question per selected videos. Outputs `target_question`.
  - `transcript_router`: Classifies whether the refined question is an activities/skills overview that is not child-specific; sets `transcript_prefer`.
  - `transcript_builder`: Loads an existing cached transcript (`data/transcripts/transcript_*.txt`) if present; otherwise can compile a compact JSON transcript from selected videos.
  - `transcript_answerer`: Judges whether the transcript can answer the refined question and, if so, provides a concise answer; sets `transcript_can_answer` and seeds `per_video_answers={"transcript": ...}`.
  - `video_analyzers`: Fallback multimodal Gemini per-video analysis when transcript is insufficient or not preferred.
  - `composer`: Synthesizes a single, parent-friendly answer from `per_video_answers`. Outputs `final_answer`.
  - `followup_advisor`: Handles interactive follow-up questions, using `conversation_history`.

- State (`QAState`):
  - Inputs/outputs carried between nodes: `user_question`, `original_question`, `child_info`, `target_videos`, `target_question`, `per_video_answers`, `final_answer`.
  - Chat context: `messages` (LangGraph messages) and `conversation_history` (simple role/content log).
  - Transcript fields: `transcript_path`, `transcript_prompt_version`, `transcript_can_answer`, `transcript_answer`, `used_transcript`, `transcript_prefer`.
  - Control flags: `waiting_for_child_info` to pause/branch after child identification.

- Adapters:
  - `LLMAdapter` (`src/adapters/llm_adapter.py`):
    - Text (`call_text`) and JSON (`call_json`) via LangChain `ChatVertexAI`.
    - Video (`call_video`) via Vertex SDK `GenerativeModel` with `[prompt, Part.from_uri(gs://...)]` for true multimodality.
  - `CatalogAdapter` (`src/adapters/catalog_adapter.py`): Loads `config/videos.yaml` and resolves `video_id -> gcs_uri` and metadata.

## Execution Pathway
- Entry points:
  - CLI: `python main.py --question "..."` → `src/cli_runner.py` → `run_main_flow(...)` in `src/graph.py`.
  - Graph creation: `create_graph(...)` wires nodes and conditional edges using `StateGraph(QAState)`.

- Edges and branching (simplified):
  - Entry → `child_identifier`
  - `child_identifier` → if `waiting_for_child_info` then `END` (CLI collects input) else `video_picker`
  - `video_picker` → `question_refiner` → `transcript_router` → `transcript_builder` → `transcript_answerer` →
    - if `transcript_prefer` OR `transcript_can_answer`: `composer`
    - else: `video_analyzers` → `composer`
  - `composer` → if `conversation_history` present then `followup_advisor` → `END` else `END`

- ASCII flow:
```
child_identifier --(needs child info)--> END
       | (has child info)
       v
video_picker -> question_refiner -> transcript_router -> transcript_builder -> transcript_answerer --(prefer/can)--> composer
                                                                                                               \--(else)--> video_analyzers -> composer
composer --(has history?)--> followup_advisor -> END
            \--(no)-------------------------/
```

- Multimodal step details:
  - In `video_analyzers`, for each `video_id`, we build a prompt from `prompts/video_analyzer.txt` + `target_question` + optional `child_info`.
  - We resolve the GCS URI with `CatalogAdapter.get_uri(video_id)` and call `LLMAdapter.call_video(prompt, gcs_uri)`.
  - `call_video` sends `[prompt, Part.from_uri(gcs_uri, mime_type="video/mp4")]` to `GenerativeModel('gemini-2.5-flash')` and returns the grounded response.

## Transcript Fast Path Details
- One-time transcript: Generate with `python -m scripts.generate_transcript`; stored at `data/transcripts/transcript_YYYY-MM-DD.txt`.
- Router logic: `transcript_router` forces transcript usage for non–child-specific “activities overview” and “skills overview” questions (e.g., “What were the activities done?”, “What skills were worked on?” and close paraphrases). Otherwise, it falls back to the normal gate.
- Gate logic: `transcript_answerer` reads either the text transcript or a compact JSON transcript, returns `{can_answer, confidence, answer, reason}`. If `confidence ≥ 0.6` or `transcript_prefer=true`, we skip analyzers and go straight to the composer.
- Composer: Unchanged; now guided by prompt to keep answers ≤160 words and no longer truncated in code.

## Recent Improvements
- Removed hard 140-word truncations in `composer` and `followup_advisor`; enforced length via prompts (≤160 words, one paragraph, no preamble).
- Added transcript-first path with caching and gating:
  - New prompts: `prompts/transcript_full_day.txt`, `prompts/transcript_answerer.txt`, `prompts/transcript_router.txt`.
  - New nodes: `src/nodes/transcript_builder.py`, `src/nodes/transcript_answerer.py`, `src/nodes/transcript_router.py`.
  - One-time generator: `scripts/generate_transcript.py` writes `data/transcripts/transcript_YYYY-MM-DD.txt`.
- Hardened JSON parsing in `LLMAdapter.call_json` to strip markdown fences and extract JSON blocks, preventing accidental fallbacks when models wrap JSON in code fences.

## Notes
- Vertex AI project: The runtime uses `GOOGLE_CLOUD_PROJECT`. The one-time generator will default to `clever-environs-458604-c8` if the env var is not set; change this in `scripts/generate_transcript.py` if needed.
- Catalog: Ensure `config/videos.yaml` GCS URIs are accessible to the active credentials.
- Add nodes by creating `src/nodes/<name>.py` and registering in `create_graph` with appropriate edges.
- Modify prompts in `prompts/` to tune behavior without code changes.
- To analyze non-MP4 videos, add a `mime_type` field in `config/videos.yaml` and adapt `LLMAdapter.call_video` accordingly.

## Testing
Run test scripts:
```bash
python tests/test_child_identification.py
python tests/test_system_flow.py
python tests/test_cli_fix.py
python tests/test_vertex_ai.py
```

## Troubleshooting
- Permission errors or empty answers:
  - Run `gcloud auth application-default login` again and verify `GOOGLE_CLOUD_PROJECT`.
  - Ensure the ADC identity has `storage.objects.get` on your video objects.
- Model/region issues:
  - The default region is `us-central1`. If your project uses a different region, update `location` in `LLMAdapter`.
- Video format:
  - The adapter uses `mime_type="video/mp4"`. If your videos differ, add a `mime_type` to your catalog and update `LLMAdapter.call_video` accordingly.
- Still getting generic answers:
  - Lower temperature in `LLMAdapter.call_video` to `0.2`.
  - Tighten the analyzer prompt in `prompts/video_analyzer.txt` with more explicit constraints.
