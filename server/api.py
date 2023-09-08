import os
from typing import List
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import openai

from schema import ChatMessage, ChatRequest, ModelsRequest, OpenAIModelID, Config

error503 = "OpenAI server is busy, try again later"


class Api:
    def __init__(self, app: FastAPI, config: Config):
        self.router = APIRouter()
        self.app = app
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

    def main(self):
        web_app_dir = "/Users/cwq/code/github/chatbot-ui/out"
        return FileResponse(os.path.join(web_app_dir, "index.html"))

    def models(self, req: ModelsRequest) -> List[dict]:
        all_models = openai.Model.list(req.key)
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

    error503 = "OpenAI server is busy, try again later"

    def chat(self, req: ChatRequest):
        messages = req.messages
        if req.prompt:
            messages.insert(0, ChatMessage(role="system", content=req.prompt))

        openai.api_key = req.key

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
                print("Error in creating campaigns from openAI:", str(e))
                raise HTTPException(503, error503)

            try:
                for chunk in stream_response:
                    current_content = chunk["choices"][0]["delta"].get("content", "")
                    yield current_content

            except Exception as e:
                print("OpenAI Response (Streaming) Error: " + str(e))
                raise HTTPException(503, error503)

        return StreamingResponse(content=gen(), media_type="text/event-stream")

    def add_api_route(self, path: str, endpoint, **kwargs):
        return self.app.add_api_route(path, endpoint, **kwargs)
