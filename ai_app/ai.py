from google import genai
from decouple import config
import logging

logger = logging.getLogger("ai")

api_key = config("GEMINI_API_KEY", default=None)

class Ai_Agent:
    def __init__(self):
        
        if not api_key:
            raise ValueError ("Gemini API key not found in environment variables.")
        try:
             self.client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.critical("Gemini API key not found in environment variables.")
            raise ValueError(f"Failed to configure Google Generative AI: {e}") from e
       
    
    
    def gemini_response(self, user_text, *args, **kwargs):
        logger.debug(f"Sending request to Gemini API: '{user_text[:50]}...'")
        try:
            system_prompt = """
             You are an expert programming assistant integrated into Telex IM, powered by Google Gemini.
                Your primary goal is to help developers by providing clear, concise, and accurate explanations or code examples.
                - Answer questions about programming languages (especially Python, Django, JavaScript), frameworks, concepts, algorithms, etc.
                - If asked to fix code, identify the problem and suggest a corrected version.
                - If asked to explain code, break it down step-by-step.
                - Prefer Python, Django, or general pseudocode unless specified otherwise.
                - Keep explanations beginner-friendly but accurate.
                - If you don't know the answer, say "I'm sorry, I don't have enough information to answer that specific question."
                - Do not hallucinate code libraries or functions that don't exist.
                - Format code snippets using triple backticks (```) for readability.
                Example response format:
                You can loop through a list in Python using a `for` loop:
                ```python
                my_list = ['item1', 'item2', 'item3']
                for item in my_list:
                    print(item)
                ```
                This iterates over each element (`item`) in `my_list
                
            """
            user_text = user_text
            gemini_response =  self.client.models.generate_content(model="gemini-2.5-flash", contents = f"{system_prompt} and here your question = {user_text}"
                
            )
            
            
            
            response = gemini_response.candidates[0].content.parts[0].text
            logger.info(f"Received response from Gemini API: '{response[:50]}...'")
            return response
        
        except Exception as e:
            logger.error(f"Error connecting to Gemini API: {e}", exc_info=True)
            return (f'there was an error connecting to gemini via api, please make sure api is valid error:{e}')