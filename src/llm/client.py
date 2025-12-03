from google import genai
from google.genai import types
from pydantic import BaseModel

# Import only the simple, static configurations from settings
from src.config.settings import GEMINI_API_KEY
# Import the config loader directly
from src.config.config_loader import load_config
from src.llm.registry import tool_registry


class LLMToolModel(BaseModel):
    function_declarations: list[types.FunctionDeclaration] = []

    @property
    def get_tool(self):
        return types.Tool(
            function_declarations=self.function_declarations
        )

# --- Global Instances ---
# Load the LLM configuration here, breaking the circular import.
LLM_CONFIG = load_config()

_gemini_api_key = GEMINI_API_KEY
# The client gets the API key from the environment variable `GEMINI_API_KEY`.
_client = genai.Client(api_key=_gemini_api_key)

class MCGeminiLLM:
    def __init__(self, client: genai.Client):
        self.model: str = LLM_CONFIG.model
        self.config: types.GenerateContentConfig = LLM_CONFIG.generate_content_config
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
    # The MCGeminiLLM class correctly loads the configuration,
    # including tools, from LLM_CONFIG. No changes are needed there.
    mc_gemini_llm = MCGeminiLLM(_client)
    chat = mc_gemini_llm.get_chat()

    print("Chat with Gemini. Type 'exit' to end the conversation.")

    while True:
        user_prompt = input("\n> ")
        if user_prompt in ["e", "exit"]:
            break

        try:
            response = chat.send_message(user_prompt)

            # This loop continues as long as the model requests function calls.
            # It has a safety break after 5 iterations to prevent infinite loops.
            for _ in range(5):  # Max 5 sequential function calls
                part = next(part for part in response.parts)

                if not part.function_call:
                    # If there's no function call, we have our final text response.
                    break

                # --- Execute the function call ---
                function_call = part.function_call
                function_name = function_call.name
                print(f"LLM wants to call function: {function_name}({dict(function_call.args)})")

                try:
                    # 1. Look up the implementation and call it with the provided arguments.
                    tool_function = tool_registry.implementations[function_name]
                    function_result = tool_function(**dict(function_call.args))

                    # 2. Send the function's result back to the model.
                    response = chat.send_message(
                        types.Part(function_response=types.FunctionResponse(
                            name=function_name,
                            response={"result": function_result},
                        ))
                    )
                except Exception as e:
                    print(f"Error during function call '{function_name}': {e}")
                    break # Exit loop on error

            # After the loop, print the final text response from the LLM.
            if response.parts[0].text:
                print(f"\nLLM: {response.parts[0].text}")

        except Exception as e:
            print(f"An error occurred: {e}")
