# QAState – Agentic Path

**Purpose:** Shared state object passed between nodes in LangGraph.  
All fields must be explicitly read/written by specific nodes.

| Field | Type | Description | Written by | Read by |
|-------|------|-------------|------------|---------|
| `user_question` | string | Original parent question | entry point | all |
| `target_videos` | list of strings | Video IDs selected for deep analysis | video_picker | video_analyzers, composer |
| `target_question` | string | Refined question for per-video analysis | question_refiner | video_analyzers |
| `per_video_answers` | dict {video_id: string} | Answers from each video analyzer | video_analyzers | composer |
| `final_answer` | string | Synthesized answer to user_question | composer | followup_advisor |
| `conversation_history` | list of dicts `{role, content}` | Running chat history with parent | followup_advisor | followup_advisor |
| `followup_response` | string | Response to a follow-up question | followup_advisor | output |
