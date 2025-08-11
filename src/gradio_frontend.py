"""
Gradio Frontend for Agentic Video QA System
Simple chatbot interface that connects to the FastAPI backend
"""

import gradio as gr
import requests
import json
from typing import List, Tuple

# API configuration
API_BASE_URL = "http://localhost:8000"

class VideoQAChatbot:
    def __init__(self):
        self.conversation_history = []
        self.final_answer = ""
        self.target_videos = []
    
    def ask_question(self, question: str) -> Tuple[str, List[List[str]]]:
        """Ask a question and get the answer"""
        try:
            # Call the API
            response = requests.post(
                f"{API_BASE_URL}/ask",
                json={"question": question}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Store for follow-up questions
            self.final_answer = data["final_answer"]
            self.target_videos = data["target_videos"]
            
            # Add to conversation history
            self.conversation_history.append(["user", question])
            self.conversation_history.append(["assistant", data["final_answer"]])
            
            # Return the conversation
            return "", self.conversation_history
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error connecting to API: {str(e)}"
            self.conversation_history.append(["user", question])
            self.conversation_history.append(["assistant", error_msg])
            return "", self.conversation_history
    
    def followup_question(self, followup: str) -> Tuple[str, List[List[str]]]:
        """Ask a follow-up question"""
        if not self.final_answer:
            error_msg = "Please ask an initial question first."
            self.conversation_history.append(["user", followup])
            self.conversation_history.append(["assistant", error_msg])
            return "", self.conversation_history
        
        try:
            # Prepare history for API
            history = []
            for msg in self.conversation_history:
                if len(msg) == 2:
                    history.append({
                        "role": msg[0],
                        "content": msg[1]
                    })
            
            # Call the follow-up API
            response = requests.post(
                f"{API_BASE_URL}/followup",
                json={
                    "question": followup,
                    "final_answer": self.final_answer,
                    "history": history
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Add to conversation history
            self.conversation_history.append(["user", followup])
            self.conversation_history.append(["assistant", data["followup_response"]])
            
            # Return the conversation
            return "", self.conversation_history
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error connecting to API: {str(e)}"
            self.conversation_history.append(["user", followup])
            self.conversation_history.append(["assistant", error_msg])
            return "", self.conversation_history
    
    def clear_history(self) -> Tuple[str, List[List[str]]]:
        """Clear conversation history"""
        self.conversation_history = []
        self.final_answer = ""
        self.target_videos = []
        return "", []

def create_interface():
    """Create the Gradio interface"""
    
    chatbot = VideoQAChatbot()
    
    with gr.Blocks(
        title="Agentic Video QA System",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 800px;
            margin: 0 auto;
        }
        """
    ) as interface:
        
        gr.Markdown("""
        # 🎥 Agentic Video QA System
        
        Ask questions about your child's preschool day captured in videos. The AI will analyze relevant video segments and provide detailed answers.
        
        **How to use:**
        1. Ask your initial question in the first input
        2. Review the AI's analysis and answer
        3. Ask follow-up questions for more details or actionable advice
        """)
        
        with gr.Row():
            with gr.Column(scale=3):
                # Initial question input
                initial_question = gr.Textbox(
                    label="Ask about your child's day",
                    placeholder="e.g., Did the teacher run any small-group activity after circle time?",
                    lines=2
                )
                ask_btn = gr.Button("Ask Question", variant="primary")
            
            with gr.Column(scale=1):
                clear_btn = gr.Button("Clear Chat", variant="secondary")
        
        # Follow-up question input
        followup_question = gr.Textbox(
            label="Follow-up question",
            placeholder="e.g., What can I do at home to reinforce this?",
            lines=2
        )
        followup_btn = gr.Button("Ask Follow-up", variant="primary")
        
        # Chat display
        chat_display = gr.Chatbot(
            label="Conversation",
            height=400,
            show_label=True
        )
        
        # Video info display
        video_info = gr.Markdown("")
        
        # Event handlers
        ask_btn.click(
            fn=chatbot.ask_question,
            inputs=[initial_question],
            outputs=[initial_question, chat_display]
        ).then(
            fn=lambda: f"**Videos Analyzed:** {', '.join(chatbot.target_videos) if chatbot.target_videos else 'None'}",
            outputs=[video_info]
        )
        
        followup_btn.click(
            fn=chatbot.followup_question,
            inputs=[followup_question],
            outputs=[followup_question, chat_display]
        )
        
        clear_btn.click(
            fn=chatbot.clear_history,
            outputs=[initial_question, chat_display, video_info]
        )
        
        # Enter key support
        initial_question.submit(
            fn=chatbot.ask_question,
            inputs=[initial_question],
            outputs=[initial_question, chat_display]
        ).then(
            fn=lambda: f"**Videos Analyzed:** {', '.join(chatbot.target_videos) if chatbot.target_videos else 'None'}",
            outputs=[video_info]
        )
        
        followup_question.submit(
            fn=chatbot.followup_question,
            inputs=[followup_question],
            outputs=[followup_question, chat_display]
        )
        
        gr.Markdown("""
        ---
        **Note:** This system analyzes preschool video recordings to answer questions about your child's activities, behavior, and learning experiences.
        """)
    
    return interface

if __name__ == "__main__":
    # Create and launch the interface
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
