# Agentic Video QA System

An AI-powered video question-answering system designed specifically for preschool video analysis. Parents can ask questions about their children's activities, behavior, and learning experiences captured in daily video recordings.

## 🎯 What It Does

The system intelligently:
1. **Identifies your child** by name and clothing description to focus the analysis
2. **Selects relevant videos** from a day's recordings based on your question
3. **Analyzes video content** using Gemini 2.5 Flash's multimodal capabilities, focusing on your child
4. **Synthesizes answers** into parent-friendly responses
5. **Handles follow-up questions** with actionable advice and guidance

## 🏗️ Architecture

- **LangGraph-based workflow** with pure function nodes
- **Parallel video processing** (up to 3 concurrent analyses)
- **Strict I/O contracts** - each node writes exactly specified fields
- **Adapters** for LLM (Gemini) and catalog management
- **Config-driven** settings and fallbacks

### Node Flow
```
child_identifier → video_picker → question_refiner → video_analyzers (parallel) → composer → followup_advisor
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
export GOOGLE_API_KEY="your_gemini_api_key_here"
```

### 3. Configure Videos
Update `config/videos.yaml` with your actual GCS video URIs:
```yaml
videos:
  - id: vid_1
    gcs_uri: gs://your-bucket/path/video1.mp4
    session-type: "Circle"
    start-time: 30
    end-time: 30
    act-description: "Morning circle time activities"
```

### 4. Run the System

#### CLI Mode (Test First)
```bash
python main.py cli --question "Did the teacher run any small-group activity after circle time?"
```
**Note:** The system will first ask for your child's name and clothing description to focus the analysis.

#### API Mode (Backend)
```bash
python main.py api --port 8000
```

#### Gradio Frontend
```bash
python main.py gradio --gradio-port 7860
```

## 📱 Usage Examples

### Initial Question
**Q:** "Did the teacher run any small-group activity after circle time?"

**System Response:**
- Picks relevant videos (e.g., vid_2, vid_3, vid_4, vid_5)
- Analyzes each video for evidence
- Provides synthesized answer with time ranges

### Follow-up Question
**Q:** "What can I do at home to reinforce this?"

**System Response:**
- Actionable advice based on the activity
- Specific steps for home reinforcement
- Maintains conversation context

## 🔧 Configuration

### `config/app.yaml`
```yaml
max_videos_in_deep_path: 5
model_name: gemini-2.5-flash
```

### `config/videos.yaml`
- Video metadata and GCS URIs
- Session types: Circle, Activity, Meal
- Timing and activity descriptions

## 🧪 Testing

### Acceptance Test 1
**Question:** "Did the teacher run any small-group activity after circle time?"
**Expected:** 
- Picker selects 1-5 relevant video IDs
- Analyzers provide paragraphs with time ranges
- Composer outputs one-paragraph final answer

### Acceptance Test 2
**Question:** "How long was outdoor play and what did kids do?"
**Follow-up:** "What can I do at home to reinforce this?"
**Expected:** 
- Similar analysis flow
- Follow-up advisor returns 2-4 actionable steps

## 🛡️ Guardrails & Fallbacks

- **JSON parsing failures:** Retry with temperature=0.0
- **Video timeouts:** Graceful degradation to "Not enough evidence"
- **Response length:** Enforced 140-word limit for composer
- **Logging safety:** GCS URIs truncated in public logs

## 📊 Logging

Each node logs:
- Request ID
- Node name
- Duration (ms)
- Output fields set
- Target videos/video IDs

## 🔌 API Endpoints

### POST `/ask`
Process a question through the main flow.

**Request:**
```json
{
  "question": "Did the teacher run any small-group activity after circle time?"
}
```

**Response:**
```json
{
  "final_answer": "Based on the video analysis...",
  "target_videos": ["vid_2", "vid_3"],
  "per_video_answers": {
    "vid_2": "The teacher organized...",
    "vid_3": "Small groups were formed..."
  }
}
```

### POST `/followup`
Handle follow-up questions.

**Request:**
```json
{
  "question": "What can I do at home to reinforce this?",
  "final_answer": "Based on the video analysis...",
  "history": [
    {"role": "user", "content": "Original question..."},
    {"role": "assistant", "content": "Original answer..."}
  ]
}
```

**Response:**
```json
{
  "followup_response": "Here are some actionable steps..."
}
```

## 🏃‍♂️ Development

### Project Structure
```
src/
├── adapters/          # LLM and catalog adapters
├── nodes/            # Pure function nodes
├── state.py          # State management
├── graph.py          # LangGraph workflow
├── cli_runner.py     # Command-line interface
├── api.py            # FastAPI backend
└── gradio_frontend.py # Web interface
```

### Adding New Nodes
1. Create function in `src/nodes/`
2. Follow strict I/O contract from `.plan.md`
3. Add to graph in `src/graph.py`
4. Update state schema if needed

## 🚨 Troubleshooting

### Common Issues

**"GOOGLE_API_KEY not set"**
- Ensure environment variable is set
- Restart terminal/IDE after setting

**"Invalid GCS URI"**
- Check `config/videos.yaml` format
- Ensure URIs start with `gs://`

**"Video analysis timeout"**
- Check network connectivity to GCS
- Verify service account permissions

**"JSON parse error"**
- System will retry with stricter settings
- Check prompt templates for JSON formatting

## 📄 License

This project is designed for educational and research purposes. Please ensure compliance with your organization's data handling policies when processing video content.

## 🤝 Contributing

1. Follow the established node contract patterns
2. Maintain strict I/O field specifications
3. Add comprehensive logging
4. Include fallback behaviors
5. Test with acceptance criteria
