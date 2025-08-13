# Agentic Video QA System (Transcript-First Demo)

A streamlined, transcript-first demo for preschool video QA. Ask a question, identify the child (Ayaan in demo), and get a concise answer sourced from pre-generated transcripts. The demo does not invoke multimodal video analyzers.

## Project Structure
```
config/                 # Video metadata (videos.yaml)
prompts/                # Prompt templates used by the demo
src/                    # Core source (graph, nodes, adapters, CLI)
scripts/                # Utility scripts (prep, child transcripts from image)
data/transcripts/       # Day transcripts (committed)
data/child_transcripts/ # Per-child transcripts (committed)
data/snippedvideos/     # Local evidence clips (ignored)
tests/                  # Unit tests
README.md               # This guide
requirements.txt        # Python deps
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
4. Authenticate to Google Cloud (only needed for transcript generation prep; not required to run the demo):
   ```bash
   gcloud auth application-default login
   ```
   - Ensure the active credentials have access to the GCS bucket objects (at least `roles/storage.objectViewer`).
   - Enable the Vertex AI and Cloud Storage APIs for your project.

5. Configure video catalog in `config/videos.yaml` (for prep only, not required to run the demo):
   - Open the file, remove or update the sample entries, and add your own video metadata.
   - Each entry must include a `gcs_uri` (for example `gs://bucket/path/video.mp4`).
   - Optional fields like `session-type`, `start-time`, and `end-time` can be either numeric minutes or `HH:MM` strings.

## Usage
### Demo Run (Transcript-Only)
- Parent: Sounak; Child: Ayaan.
- The demo uses transcripts only and never calls multimodal video analyzers.

Run the interactive demo:
```bash
python main.py --demo
```
- You’ll be prompted for a question. The system answers using the day transcript and child transcript (if available) for Ayaan.
- Follow-up routing remains: generate evidence clip, retrigger transcript analysis, or start parent advisor.

Non-interactive mode (without demo banner, still transcript-first):
```bash
python main.py --question "What activities did Ayaan do today?" --transcripts-only
```

### Prepare Child Transcript From Image (Optional Prep)
Use only when you locally have the child’s image and access to the GCS videos. This generates per-video child transcripts guided by a local image using the unified `child_mood_analyzer` prompt.
```bash
python -m scripts.generate_child_from_image --image /path/to/ayaan.jpg --confirm
```
- Output: `data/child_transcripts/by_image/YYYY-MM-DD/<image-slug>/<video_id>.json`
- Schema: `{ video_id, child_label, observed, engagement_level, mood[], behaviors[], distress_events[], evidence_times[], short_per_video_summary }`.

Note: Do not commit any videos. The transcripts under `data/transcripts/` and `data/child_transcripts/` are committed; videos and clips are ignored by git. A Google Drive link to input videos will be shared separately in Slack for internal prep only.

## Architecture
- Graph and nodes: `src/graph.py`, `src/nodes/`; state: `src/state.py`.

- Demo node order (transcript-only path):
  - `child_identifier` → `video_picker` → `question_refiner` → `transcript_builder` → `transcript_answerer` → `composer` → optional `followup_advisor`

ASCII demo flow:
```
child_identifier --(needs child info)--> END
       | (has child info)
       v
video_picker -> question_refiner -> transcript_builder -> transcript_answerer --(can)--> composer
                                                                                 \--(else; transcripts-only)--> composer (polite fallback)
composer --(has history?)--> followup_advisor -> END
            \--(no)-------------------------/
```

- Fallback semantics in demo: If the transcript cannot answer, we do not call video analyzers; we synthesize a polite fallback and continue into composer. Follow-ups can still ask to generate evidence clips locally or re-route through transcript analysis.

### Full Graph (Reference)
- The full graph includes transcript routing and video analyzers for fallback beyond the demo scope.
- Node order (simplified):
  - `child_identifier` → `video_picker` → `question_refiner` → `transcript_router` → `transcript_builder` → `transcript_answerer` →
    - if transcript can answer: `composer`
    - else: `video_analyzers` → `composer`
  - `composer` → optional `followup_advisor`

ASCII full flow:
```
child_identifier --(needs child info)--> END
       | (has child info)
       v
video_picker -> question_refiner -> transcript_router -> transcript_builder -> transcript_answerer --(prefer/can)--> composer
                                                                                                   \--(else)--> video_analyzers -> composer
composer --(has history?)--> followup_advisor -> END
            \--(no)-------------------------/
```

- Note: The demo uses only the transcript-first path and does not invoke `video_analyzers`. Some prompts supporting the full graph are archived for now; see Archived Prompts below.

## Clean Run Path
- Demo interactive:
  - `python main.py --demo`
  - Answer is produced using `data/transcripts/**` and any available `data/child_transcripts/**`.

- Non-interactive (transcripts-only):
  - `python main.py --question "..." --transcripts-only`

- Optional prep (internal only):
  - Generate day transcript text/JSON (offline, requires GCS/Vertex). Do not run for demo; instead use provided committed transcripts. A Google Drive link to inputs will be shared in Slack.
  - Generate child transcripts from image:
    - `python -m scripts.generate_child_from_image --image /path/to/ayaan.jpg --confirm`

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

## Notes and Hygiene
- No videos in git. `.gitignore` excludes videos and clips under `data/` but includes transcripts and child transcripts.
- Transcripts are committed under `data/transcripts/**` and `data/child_transcripts/**`.
- Prep scripts are optional and for internal use only.
- The demo flow targets the parent Sounak and child Ayaan.

## Archived Prompts
- Purpose: These capture alternative paths and variations we explored to get things running. They are not used by the transcript-only demo but remain as reference.
- Location: `prompts_archive/`
- Includes:
  - `child_image_analyzer.txt` and `child_simple_analyzer.txt` (older child-per-video variants)
  - `parent_coach.txt` (earlier parenting helper wording)
  - `transcript_one_time.txt` (text-first transcript variant)
  - `transcript_router.txt` (router used by the full-graph reference above)

## Follow-ups
- After the first answer, the CLI offers:
  - Generate evidence clip(s) locally
  - Retrigger transcript analysis route
  - Start parent advisor

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
