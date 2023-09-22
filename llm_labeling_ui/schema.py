import uuid
from typing import List
from pathlib import Path

from pydantic import BaseModel, Field
from sqlmodel import SQLModel
from llm_labeling_ui.utils import MESSAGE_FILTER_NONE
from llm_labeling_ui.db_schema import Conversation as DBConversation

OpenAIModelID = {
    "gpt-3.5-turbo": "GPT_3_5",
    "gpt-35-turbo": "GPT_3_5_AZ",
    "gpt-4": "GPT_4",
    "gpt-4-32k": "GPT_4_32K",
}


class ModelsRequest(BaseModel):
    key: str
    org: str


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
    org: str
    prompt: str = ""
    temperature: float = 1.0


class ModelInfo(SQLModel):
    id: str = "gpt-3.5-turbo"
    name: str = "GPT-3.5"
    maxLength: int = 12000
    tokenLimit: int = 4000


class Folder(BaseModel):
    id: str = Field(default_factory=uuid.uuid4)
    name: str
    type: str = "chat"


class PromptTemp(BaseModel):
    id: str = Field(default_factory=uuid.uuid4)
    name: str
    description: str
    content: str
    model: ModelInfo
    folderId: str = None


class Message(BaseModel):
    role: str
    content: str


class Conversation(BaseModel):
    id: str = Field(default_factory=uuid.uuid4)
    name: str = ""
    messages: List[Message] = []
    model: ModelInfo = ModelInfo()
    # system
    prompt: str = ""
    temperature: int = 1
    folderId: str = None

    def merged_text(self) -> str:
        return "".join([self.prompt] + [m.content for m in self.messages])


class ChatBotUIHistory(BaseModel):
    version: int = 4
    history: List[Conversation] = []
    folders: List[Folder] = []
    prompts: List[PromptTemp] = []


class Config(BaseModel):
    web_app_dir: Path


class GetConversionsRequest(BaseModel):
    page: int = 0
    pageSize: int = 50
    searchTerm: str = ""
    messageCountFilterCount: int = 0
    messageCountFilterMode: str = MESSAGE_FILTER_NONE


class GetConversionsResponse(BaseModel):
    page: int
    totalPages: int
    conversations: List[DBConversation]
    totalConversations: int


class CountTokensRequest(BaseModel):
    text: str


class CountTokensResponse(BaseModel):
    count: int
