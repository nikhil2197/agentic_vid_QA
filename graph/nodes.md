# Nodes & Responsibilities – Agentic Path
## 0. child_identifier (Child ID Required)
- **Input:** `user_question` (original question)
- **Process:**
  - Classify whether the user's question requires focusing on a specific child.
  - If yes, prompt the user for the child's name and clothing description.
- **Output:**
  - `original_question` stored if prompting, `child_info` collected, `waiting_for_child_info` flag, updated `user_question` for prompt.

## 1. video_picker
- **Input:** `user_question`, `videos.yaml` catalog  
- **Process:**  
  - Load prompt `video_picker.txt`  
  - Feed catalog + question to Gemini 2.5 Flash  
- **Output:** `target_videos` (up to 5 IDs)

## 2. question_refiner
- **Input:** `user_question`  
- **Process:**  
  - Load prompt `question_refiner.txt`  
  - Refine for a single video  
- **Output:** `target_question`

## 3. video_analyzers *(parallel node for each selected video)*
- **Input:** `target_question`, `target_videos`  
- **Process:**  
  - For each video:  
    - Load prompt `video_analyzer.txt`  
    - Pass video URI + `target_question` to Gemini 2.5 Flash (video multimodal input)  
- **Output:** `per_video_answers` (map: id → answer)

## 4. composer
- **Input:** `user_question`, `per_video_answers`  
- **Process:**  
  - Load prompt `composer.txt`  
  - Synthesize a single final answer  
- **Output:** `final_answer`

## 5. followup_advisor
- **Input:** `user_question`, `final_answer`, `conversation_history`  
- **Process:**  
  - Load prompt `followup_advisor.txt`  
  - Append conversation history  
  - Generate follow-up advice or answer  
- **Output:** `followup_response`
