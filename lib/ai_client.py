import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai

load_dotenv()

class AIClient:
    def __init__(self):
        # Gemini Init
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("WARNING: GOOGLE_API_KEY is not set.")
        self.client = genai.Client(api_key=self.api_key)

        # OpenAI Compatible Init (e.g. LM Studio)
        self.llm_api_base = os.getenv("LLM_API_BASE")
        self.llm_api_key = os.getenv("LLM_API_KEY", "lm-studio")
        self.openai_client = None
        if self.llm_api_base:
            print(f"Initializing OpenAI Client with base: {self.llm_api_base}")
            self.openai_client = openai.OpenAI(
                base_url=self.llm_api_base,
                api_key=self.llm_api_key
            )

    @retry(
        retry=retry_if_exception_type(Exception), 
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5)
    )
    def generate_tags(self, filename: str, filepath: str, existing_tags: dict) -> dict:
        """
        Generate metadata tags for a sound effect (SE) using Gemini API by analyzing the audio file.
        """
        try:
            # Upload the file
            print(f"Uploading {filename} to Gemini...", flush=True)
            with open(filepath, "rb") as f:
                audio_file = self.client.files.upload(file=f, config={'mime_type': 'audio/mp3'})
            
            prompt = f"""
            Analyze the following audio file (Sound Effect) and generate metadata tags.
            
            Filename: {filename}
            Existing Tags (from file): {existing_tags}
            
            Please provide the following information in JSON format:
            - title: A descriptive name for the sound (e.g., "Heavy Rain", "Door Creak").
            - artist: The **Category** of the sound (e.g., "Nature", "UI", "Impact", "Vehicle").
            - album: The **Sub-Category** or Library name if inferable.
            - genre: The **Mood** or **Type** (e.g., "Dark", "Bright", "Retro", "Realistic").
            - year: (YYYY) leave as null or current year.
            - comment: A detailed description of the sound and its potential usage.
            
            Return ONLY valid JSON.
            """

            response = self.client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                contents=[prompt, audio_file],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            return json.loads(response.text)
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            raise e

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3)
    )
    def expand_query(self, query: str) -> list[str]:
        """
        Expand a natural language query into a list of search keywords.
        Uses OpenAI compatible API if configured, otherwise Gemini.
        """
        system_prompt = """
        You are a search assistant for a sound effect database.
        Extract 5-10 relevant search keywords or short phrases (in English or Japanese) that would match potential filenames, categories, moods, or descriptions.
        Return the result as a JSON list of strings.
        Example: ["keyword1", "keyword2"]
        """
        user_prompt = f'Query: "{query}"'

        if self.openai_client:
            try:
                # Use Local LLM
                model_name = os.getenv("LLM_MODEL", "local-model")
                response = self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                )
                content = response.choices[0].message.content
                # Attempt to extract JSON list from content if it contains extra text
                # Simple check: find '[' and ']'
                start = content.find('[')
                end = content.rfind(']')
                if start != -1 and end != -1:
                    json_str = content[start:end+1]
                    return json.loads(json_str)
                return json.loads(content)
            except Exception as e:
                print(f"Error calling OpenAI API: {e}")
                # Fallback to simple split? Or re-raise? 
                # For now, let's fall back to Gemini if available, or just split
                pass

        # Fallback to Gemini
        prompt = f"""
        {system_prompt}
        {user_prompt}
        """
        
        try:
            response = self.client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Error expanding query with Gemini: {e}")
            return query.split()
