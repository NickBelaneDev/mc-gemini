import tomli

from pydantic import BaseModel, Field
from google.genai import types

CONFIG_PATH = "mc_llm_config.toml"

class LLMConfigModel(BaseModel):
    model: str = "gemini-flash-latest"
    thinking_budget: int = Field(..., ge=0, le=1)
    temperature: float = Field(..., ge=0, le=2)
    max_output_tokens: int = 100
    system_instruction: str = "You are a Minecraft expert who has absolutely no idea."

    @property
    def get_content_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            system_instruction=self.system_instruction,
        )

    @property
    def get_model(self) -> str:
        return self.model

def load_config() -> LLMConfigModel:
    """Loads and returns a BaseModel of the config.toml."""
    with open(CONFIG_PATH, "rb") as f:
        raw = tomli.load(f)
    print(f"{f} loaded!")
    return LLMConfigModel(**raw["config"])


if __name__ == "__main__":
    config = load_config()
    print(config.get_content_config)
