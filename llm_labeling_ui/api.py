import math
import os
from functools import lru_cache
from typing import List
from pathlib import Path
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import openai
from loguru import logger

from llm_labeling_ui.db_schema import (
    DBManager,
    Folder,
    PromptTemp,
    Conversation as DBConversation,
)
from llm_labeling_ui.schema import (
    ChatMessage,
    ChatRequest,
    ModelsRequest,
    OpenAIModelID,
    Config,
    GetConversionsRequest,
    GetConversionsResponse,
    Conversation,
    CountTokensResponse,
    CountTokensRequest,
)

error503 = "OpenAI server is busy, try again later"


class Api:
    def __init__(self, app: FastAPI, config: Config, db: DBManager, tokenizer=None):
        self.router = APIRouter()
        self.app = app
        self.db = db
        self.tokenizer = tokenizer
        self.config = config
        if self.tokenizer is not None:
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.tokenizer, trust_remote_code=True
            )

        self.app.mount(
            "/static", StaticFiles(directory=config.web_app_dir), name="static"
        )

        self.add_api_route(
            "/",
            self.main,
            methods=["GET"],
        )

        self.add_api_route(
            "/api/models",
            self.models,
            methods=["POST"],
            response_model=List[dict],
        )

        self.add_api_route(
            "/api/chat",
            self.chat,
            methods=["POST"],
            response_model=str,
        )

        self.add_api_route(
            "/api/folders",
            self.get_folders,
            methods=["GET"],
            response_model=List[Folder],
        )

        self.add_api_route(
            "/api/prompt_temps",
            self.get_prompt_temps,
            methods=["GET"],
            response_model=List[PromptTemp],
        )

        self.add_api_route(
            "/api/conversations",
            self.get_conversations,
            methods=["POST"],
            response_model=GetConversionsResponse,
        )

        self.add_api_route(
            "/api/create_conversation",
            self.create_conversation,
            methods=["POST"],
            # response_model=Conversation,
        )

        self.add_api_route(
            "/api/update_conversation",
            self.update_conversation,
            methods=["POST"],
            # response_model=Conversation,
        )

        self.add_api_route(
            "/api/delete_conversation",
            self.delete_conversation,
            methods=["POST"],
            # response_model=Conversation,
        )

        self.add_api_route(
            "/api/count_tokens",
            self.count_tokens,
            methods=["POST"],
            response_model=CountTokensResponse,
        )

    def main(self):
        return FileResponse(os.path.join(self.config.web_app_dir, "index.html"))

    def models(self, req: ModelsRequest) -> List[dict]:
        api_key = req.key if req.key else os.environ.get("OPENAI_API_KEY")
        api_org = req.org if req.org else os.environ.get("OPENAI_ORGANIZATION")
        all_models = openai.Model.list(api_key, organization=api_org)
        res = []
        for it in all_models.data:
            if it.id in OpenAIModelID:
                res.append(
                    {
                        "id": it.id,
                        "name": OpenAIModelID[it.id],
                    }
                )
        return res

    def chat(self, req: ChatRequest):
        messages = req.messages
        if req.prompt:
            messages.insert(0, ChatMessage(role="system", content=req.prompt))

        if req.key:
            openai.api_key = req.key
        else:
            openai.api_key = os.environ.get("OPENAI_API_KEY")

        if req.org:
            openai.organization = req.org
        else:
            openai.organization = os.environ.get("OPENAI_ORGANIZATION")

        def gen():
            try:
                stream_response = openai.ChatCompletion.create(
                    model=req.model.id,
                    messages=[it.dict() for it in messages],
                    max_tokens=1000,
                    temperature=req.temperature,
                    stream=True,
                )
            except Exception as e:
                logger.error("Error in creating campaigns from openAI:", str(e))
                raise HTTPException(503, error503)

            try:
                for chunk in stream_response:
                    current_content = chunk["choices"][0]["delta"].get("content", "")
                    yield current_content

            except Exception as e:
                logger.error("OpenAI Response (Streaming) Error: " + str(e))
                raise HTTPException(503, error503)

        return StreamingResponse(content=gen(), media_type="text/event-stream")

    def get_folders(self) -> List[Folder]:
        return self.db.get_folders()

    def get_prompt_temps(self) -> List[PromptTemp]:
        return self.db.get_prompt_temps()

    def get_conversations(self, req: GetConversionsRequest) -> GetConversionsResponse:
        conversions_count = self.db.count_conversations(
            req.searchTerm, req.messageCountFilterCount, req.messageCountFilterMode
        )
        total_pages = math.ceil(conversions_count / req.pageSize)
        return GetConversionsResponse(
            conversations=self.db.get_conversations(
                page=req.page,
                page_size=req.pageSize,
                search_term=req.searchTerm,
                messageCountFilterCount=req.messageCountFilterCount,
                messageCountFilterMode=req.messageCountFilterMode,
            ),
            page=req.page,
            totalPages=total_pages,
            totalConversations=conversions_count,
        )

    def update_conversation(self, req: Conversation):
        db_req = DBConversation(id=req.id, data=req.dict())
        self.db.update_conversation(db_req)
        return "ok", 200
        # return Conversation(**db_res.data)

    def create_conversation(self, req: Conversation):
        db_req = DBConversation(id=req.id, data=req.dict())
        self.db.create_conversation(db_req)
        return "ok", 200
        # return Conversation(**db_res.data)

    def delete_conversation(self, req: Conversation):
        self.db.delete_conversation(req.id)
        return "ok", 200

    def count_tokens(self, req: CountTokensRequest) -> CountTokensResponse:
        @lru_cache(maxsize=512)
        def cached_count_tokens(text: str) -> int:
            if self.tokenizer is None:
                return 0
            else:
                return len(self.tokenizer(text)["input_ids"])

        count = cached_count_tokens(req.text)
        return CountTokensResponse(count=count)

    def add_api_route(self, path: str, endpoint, **kwargs):
        return self.app.add_api_route(path, endpoint, **kwargs)
