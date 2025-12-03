import os

from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from src.config.config_loader import load_config

load_dotenv(find_dotenv())

config = load_config()
print(config)

class LLMToolModel(BaseModel):
    function_declarations: list[types.FunctionDeclaration] = []

    @property
    def get_tool(self):
        return types.Tool(
            function_declarations=self.function_declarations
        )

_gemini_api_key = os.getenv("GEMINI_API_KEY")
# The client gets the API key from the environment variable `GEMINI_API_KEY`.
_client = genai.Client(api_key=_gemini_api_key)

class MCGeminiLLM:
    def __init__(self, client: genai.Client):
        self.model: str = config.get_model
        self.config: types.GenerateContentConfig = config.get_content_config
        self.client: genai.Client = client

    def get_chat(self):
        try:
            return self.client.chats.create(
                    model=self.model,
                    config=self.config
                    )

        except Exception as e:
            print(f"Failed to create chat!\n{e}")
            return False

    def ask(self, prompt: str):
        try:
            return self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.config
            )
        except Exception as e:
            print(f"Failed to answer!\n{e}")
            return False


if __name__ == "__main__":
    mc_gemini_llm = MCGeminiLLM(_client)
    chat = mc_gemini_llm.get_chat()


    while True:
        prompt = input("\n> ")
        if prompt in ["e", "exit"]:
            break

        response = chat.send_message(prompt)
        print("\nLLM: ", response)



