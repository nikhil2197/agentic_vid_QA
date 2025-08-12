# Graph Edges – Agentic Path

**Purpose:** Defines the order of node execution in LangGraph.

1. **Entry Point → child_identifier**  
   - Passes `user_question` from the entry state to `child_identifier`.

2. **child_identifier → video_picker**  
   - Passes `user_question`, `original_question`, and any collected `child_info` (if provided) to `video_picker`.

3. **video_picker → question_refiner**  
   - Passes `target_videos` and `user_question` to `question_refiner`.

3. **question_refiner → video_analyzers**  
   - Loops over `target_videos` in parallel.  
   - Each video analyzer receives:  
     - The corresponding `video_id` → `gcs_uri` from `videos.yaml`  
     - `target_question`

4. **video_analyzers → composer**  
   - Aggregates `per_video_answers` into state and passes to `composer`.

6. **composer → followup_advisor**  
   - Passes `final_answer` and `user_question` to `followup_advisor` along with `conversation_history` (if any).

7. **followup_advisor → END**  
   - Produces `followup_response` for the parent.  
   - End of graph run.
