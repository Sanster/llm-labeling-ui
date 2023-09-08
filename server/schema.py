from typing import List

from pydantic import BaseModel

OpenAIModelID = {
    "gpt-3.5-turbo": "GPT_3_5",
    "gpt-35-turbo": "GPT_3_5_AZ",
    "gpt-4": "GPT_4",
    "gpt-4-32k": "GPT_4_32K",
}


class ModelsRequest(BaseModel):
    key: str


class ChatMessage(BaseModel):
    role: str
    content: str


class OpenAIModel(BaseModel):
    id: str
    name: str
    maxLength: int
    tokenLimit: int


class ChatRequest(BaseModel):
    model: OpenAIModel
    messages: List[ChatMessage]
    key: str
    prompt: str = ""
    temperature: float = 1.0


class Config(BaseModel):
    web_app_dir: str
