import os
from datetime import datetime
from pathlib import Path
from typing import List
from rich import print

import typer
from gunicorn.app.base import BaseApplication
from loguru import logger
from typer import Typer
from rich.progress import track
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm_labeling_ui.db_schema import DBManager
from llm_labeling_ui.schema import Config, Conversation

typer_app = Typer(add_completion=False, pretty_exceptions_show_locals=False)


CURRENT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
web_app_dir = CURRENT_DIR / "out"


class StandaloneApplication(BaseApplication):
    def __init__(self, app, options, config, db, tokenizer):
        self.options = options or {}
        self.app = app
        self.config = config
        self.db = db
        self.tokenizer = tokenizer
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.app


def app_factory():
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def post_worker_init(worker):
    from llm_labeling_ui.api import Api

    api = Api(worker.app.app, worker.app.config, worker.app.db, worker.app.tokenizer)
    api.app.include_router(api.router)


@typer_app.command()
def start(
    host: str = typer.Option("0.0.0.0"),
    port: int = typer.Option(8000),
    data: Path = typer.Option(
        ..., exists=True, dir_okay=False, help="json or sqlite file"
    ),
    tokenizer: str = typer.Option(None),
):
    config = Config(web_app_dir=web_app_dir)
    options = {
        "bind": f"{host}:{port}",
        # 'workers': workers,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "timeout": 120,
        "post_worker_init": post_worker_init,
        "capture_output": True,
    }

    if data.suffix == ".json":
        db_path = data.with_suffix(".sqlite")
    elif data.suffix == ".sqlite":
        db_path = data
    else:
        raise ValueError(f"unknown file type {data}")

    if not db_path.exists():
        logger.info(f"create db at {db_path}")
        db = DBManager(db_path)
        db = db.create_from_json_file(data)
    else:
        logger.warning(f"loading db from {db_path}, data may be different from {data}")
        db = DBManager(db_path)

    StandaloneApplication(app_factory(), options, config, db, tokenizer).run()


@typer_app.command(help="Export db to chatbot-ui history file")
def export(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    save_path: Path = typer.Option(
        None,
        dir_okay=False,
        help="If not specified, it will be generated in the same directory as db_path, and the file name will be added with a timestamp.",
    ),
    force: bool = typer.Option(False, help="force overwrite save_path if exists"),
):
    if save_path and save_path.exists():
        if not force:
            raise FileExistsError(f"{save_path} exists, use --force to overwrite")

    if save_path is None:
        save_path = (
            db_path.parent / f"{db_path.stem}_{datetime.utcnow().timestamp()}.json"
        )
    logger.info(f"Dumping db to {save_path}")
    db = DBManager(db_path)
    db.export_to_json_file(save_path)


@typer_app.command(help="Remove conversation which is prefix of another conversation")
def remove_prefix_conversation(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = [Conversation(**it.data) for it in db.all_conversations()]
    logger.info(f"Total conversations: {len(conversations)}")

    import pygtrie

    trie = pygtrie.CharTrie()

    prefix_conversation_to_remove = []
    for it in track(conversations, description="building trie"):
        trie[it.merged_text()] = True

    for it in track(conversations, description="checking prefix"):
        if trie.has_subtrie(it.merged_text()):
            # 完全相等的 text 不会有 subtrie
            prefix_conversation_to_remove.append(it)

    logger.info(f"Found {len(prefix_conversation_to_remove)} prefix conversation")

    if run:
        for it in track(prefix_conversation_to_remove, description="removing"):
            db.delete_conversation(it.id)


@typer_app.command(help="Delete string in conversation")
def delete_string(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    string: str = typer.Option(None, help="string to delete"),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = db.all_conversations(search_term=string)
    logger.info("Preview first 5 conversations:")
    for it in conversations[:5]:
        print("-" * 100)
        print(it)

    logger.info(
        f"Total conversations {db.count_conversations()}, contains [{string}]: {len(conversations)}"
    )

    if run:
        for it in track(conversations, description="removing"):
            it.data["prompt"] = it.data["prompt"].replace(string, "")
            for m in it.data["messages"]:
                m["content"] = m["content"].replace(string, "")
            it.updated_at = datetime.utcnow()
            db.update_conversation(it)


if __name__ == "__main__":
    typer_app()
