from enum import Enum
import os
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from starlette.responses import FileResponse

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
import json
from typing import List, Optional
import openai
from fastapi import FastAPI, Query, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# web_app_dir = os.path.join(CURRENT_DIR, "web", "out")
web_app_dir = "/Users/cwq/code/github/chatbot-ui/out"
app.mount("/static", StaticFiles(directory=web_app_dir), name="static")

OpenAIModelID = {
    "gpt-3.5-turbo": "GPT_3_5",
    "gpt-35-turbo": "GPT_3_5_AZ",
    "gpt-4": "GPT_4",
    "gpt-4-32k": "GPT_4_32K",
}


class ModelsRequest(BaseModel):
    key: str


@app.get("/")
async def main():
    return FileResponse(os.path.join(web_app_dir, "index.html"))


@app.post("/api/models")
def models(req: ModelsRequest) -> List[dict]:
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
