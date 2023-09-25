import json
from datetime import datetime
import math
from pathlib import Path
from typing import Iterator, Optional, Dict, List, Union
from uuid import UUID, uuid4

import sqlmodel
from loguru import logger
from rich.progress import track
from sqlalchemy import Column, select
from sqlmodel import SQLModel, Field, create_engine, Session, JSON, col
from sqlalchemy import func

from llm_labeling_ui.utils import (
    MESSAGE_FILTER_EQUAL,
    MESSAGE_FILTER_GREATER,
    MESSAGE_FILTER_LESS,
    MESSAGE_FILTER_NONE,
)


class TimestampModel(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime]


class UUIDIDModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)


class Conversation(UUIDIDModel, TimestampModel, table=True):
    data: Dict = Field(default={}, sa_column=Column(JSON))

    def merged_text(self, max_messages: int = -1) -> str:
        if max_messages == -1:
            max_messages = len(self.data["messages"])
        return "".join(
            [self.data["prompt"]]
            + [m["content"] for m in self.data["messages"][0:max_messages]]
        )

    def messages_count(self) -> int:
        return len(self.data["messages"])

    def token_count(self, tokenizer) -> int:
        return len(tokenizer(self.merged_text())["input_ids"])

    class Config:
        arbitrary_types_allowed = True


class Folder(UUIDIDModel, TimestampModel, table=True):
    name: str
    type: str = "chat"


class PromptTemp(UUIDIDModel, TimestampModel, table=True):
    name: str
    description: str
    content: str
    model: Dict = Field(default={}, sa_column=Column(JSON))
    folderId: Optional[UUID] = None


class DBManager:
    def __init__(self, db_path: Path):
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
        )
        SQLModel.metadata.create_all(self.engine)

    def create_from_json_file(self, json_p: Path) -> "DBManager":
        from llm_labeling_ui.schema import ChatBotUIHistory

        with open(json_p, "r", encoding="utf-8") as f:
            chatbot_ui_history = ChatBotUIHistory.parse_raw(f.read())

        with Session(self.engine) as session:
            for it in track(
                chatbot_ui_history.history, description="writing history to db"
            ):
                session.add(Conversation(id=it.id, data=it.dict()))
            session.commit()

            for it in chatbot_ui_history.folders:
                session.add(Folder(data=it.dict()))
            session.commit()

            for it in chatbot_ui_history.prompts:
                session.add(PromptTemp(data=it.dict()))
            session.commit()
        return self

    def export_to_json_file(self, json_p: Path, min_messages: int, max_messages: int):
        from llm_labeling_ui.schema import (
            ChatBotUIHistory,
            Conversation as UIConversation,
        )

        chatbot_ui_history = ChatBotUIHistory()
        chatbot_ui_history.folders = self.get_folders()
        chatbot_ui_history.prompts = self.get_prompt_temps()
        with Session(self.engine) as session:
            statement = sqlmodel.select(Conversation)
            for it in track(session.exec(statement).all()):
                if min_messages <= it.messages_count() < max_messages:
                    chatbot_ui_history.history.append(UIConversation(**it.data))

        logger.info(f"export {len(chatbot_ui_history.history)} conversations")
        with open(json_p, "w", encoding="utf-8") as f:
            json.dump(chatbot_ui_history.dict(), f, ensure_ascii=False)

    def get_folders(self) -> List[Folder]:
        with Session(self.engine) as session:
            statement = sqlmodel.select(Folder)
            folders = session.exec(statement).all()
            return folders

    def get_prompt_temps(self) -> List[PromptTemp]:
        with Session(self.engine) as session:
            statement = sqlmodel.select(PromptTemp)
            prompts = session.exec(statement).all()
            return prompts

    def get_conversations(
        self,
        page: int,
        page_size: int = 50,
        search_term: Union[str, List[str]] = "",
        messageCountFilterCount: int = 0,
        messageCountFilterMode: str = MESSAGE_FILTER_NONE,
    ) -> List[Conversation]:
        limit = page_size
        offset = page * page_size
        with Session(self.engine) as session:
            statement = (
                sqlmodel.select(Conversation)
                .order_by(Conversation.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            statement = self._filter(
                statement, search_term, messageCountFilterCount, messageCountFilterMode
            )
            convs = session.exec(statement).all()
            return convs

    def get_conversations_by_ids(
        self,
        ids: List[str],
    ) -> List[Conversation]:
        with Session(self.engine) as session:
            statement = sqlmodel.select(Conversation).where(Conversation.id.in_(ids))
            convs = session.exec(statement).all()
            return convs

    def all_conversations(
        self, search_term: Union[str, List[str]] = ""
    ) -> List[Conversation]:
        return self.get_conversations(0, 1000000000, search_term=search_term)

    def gen_conversations(self, batch_size) -> Iterator[List[Conversation]]:
        total = self.count_conversations()
        total_pages = math.ceil(total / batch_size)
        for page in range(total_pages):
            yield self.get_conversations(page, batch_size)

    def count_conversations(
        self,
        search_term: str = "",
        messageCountFilterCount: int = 0,
        messageCountFilterMode: str = MESSAGE_FILTER_NONE,
    ) -> int:
        with Session(self.engine) as session:
            statement = select(func.count(Conversation.id))
            statement = self._filter(
                statement, search_term, messageCountFilterCount, messageCountFilterMode
            )
            convs = session.exec(statement).all()
            return convs[0][0]

    def update_conversation(self, conv: Conversation):
        with Session(self.engine) as session:
            statement = select(Conversation).where(Conversation.id == conv.id)
            exist_conv = session.exec(statement).one()[0]
            exist_conv.data = conv.data
            exist_conv.updated_at = datetime.utcnow()
            session.add(exist_conv)
            session.commit()
            session.refresh(exist_conv)
            # return exist_conv

    def bucket_update_conversation(self, convs: List[Conversation]):
        with Session(self.engine) as session:
            session.bulk_update_mappings(Conversation, convs)
            session.flush()
            session.commit()

    def create_conversation(self, conv: Conversation):
        with Session(self.engine) as session:
            session.add(conv)
            session.commit()
            # return conv

    def delete_conversation(self, id: Union[str, List[str]]):
        if not isinstance(id, list):
            id = [id]

        with Session(self.engine) as session:
            statement = select(Conversation).where(Conversation.id.in_(id))
            results = session.exec(statement).all()
            for r in results:
                session.delete(r[0])
            session.commit()

    def vacuum(self):
        with Session(self.engine) as session:
            session.execute("VACUUM")

    def _filter(
        self, statement, search_term, messageCountFilterCount, messageCountFilterMode
    ):
        if messageCountFilterMode == MESSAGE_FILTER_EQUAL:
            statement = statement.where(
                func.json_array_length(Conversation.data.op("->>")("messages"))
                == messageCountFilterCount
            )
        elif messageCountFilterMode == MESSAGE_FILTER_GREATER:
            statement = statement.where(
                func.json_array_length(Conversation.data.op("->>")("messages"))
                > messageCountFilterCount
            )
        elif messageCountFilterMode == MESSAGE_FILTER_LESS:
            statement = statement.where(
                func.json_array_length(Conversation.data.op("->>")("messages"))
                < messageCountFilterCount
            )

        if search_term:
            if isinstance(search_term, str):
                search_term = [search_term]

            for s in search_term:
                statement = statement.where(col(Conversation.data).contains(s))

        return statement
