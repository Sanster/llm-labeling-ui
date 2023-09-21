import json
import math
import os
from datetime import datetime
from pathlib import Path
import random
from typing import List
from rich import print

import typer
from gunicorn.app.base import BaseApplication
from loguru import logger
from rich.prompt import Prompt
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


@typer_app.command(help="Start the web server")
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
        db.vacuum()


@typer_app.command(help="Remove duplicate conversation only keep one of them")
def remove_duplicate_conversation(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = [Conversation(**it.data) for it in db.all_conversations()]
    logger.info(f"Total conversations: {len(conversations)}")

    conversation_to_remove = []
    merged_conversations = set()
    for it in track(conversations, description="finding duplicate"):
        merged_text = it.merged_text()
        if merged_text in merged_conversations:
            conversation_to_remove.append(it)
        else:
            merged_conversations.add(merged_text)

    for it in conversation_to_remove[:5]:
        print("=" * 100)
        print(it)
        print("=" * 100)

    logger.info(f"Found {len(conversation_to_remove)} duplicate conversation")

    if run:
        for it in track(conversation_to_remove, description="removing duplicates"):
            db.delete_conversation(it.id)
        db.vacuum()


@typer_app.command(help="View conversation contain certain strings")
def view_conversation(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    search: List[str] = typer.Option(..., help="string to search"),
    preview: int = typer.Option(5, help="preview count"),
):
    db = DBManager(db_path)
    conversations = [
        Conversation(**it.data) for it in db.all_conversations(search_term=search)
    ]

    for it in conversations[:preview]:
        print(it)

    logger.info(f"Total conversations: {len(conversations)}")


@typer_app.command(help="Delete conversation contain certain string")
def delete_conversation(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    search: str = typer.Option(..., help="string to search"),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = [Conversation(**it.data) for it in db.all_conversations()]
    logger.info(f"Total conversations: {len(conversations)}")

    conversation_to_remove = []
    for it in track(conversations, description="finding duplicate"):
        merged_text = it.merged_text()
        if search in merged_text:
            conversation_to_remove.append(it)

    for it in conversation_to_remove[:5]:
        print("=".center(100, "="))
        print(it)

    logger.info(f"Found {len(conversation_to_remove)} conversations to remove")

    if run:
        for it in track(conversation_to_remove, description="removing conversations"):
            db.delete_conversation(it.id)
        db.vacuum()


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
        for it in track(conversations, description="delete string"):
            it.data["prompt"] = it.data["prompt"].replace(string, "")
            for m in it.data["messages"]:
                m["content"] = m["content"].replace(string, "")
            it.updated_at = datetime.utcnow()
            db.update_conversation(it)
        db.vacuum()


@typer_app.command(help="Replace string in conversation")
def replace_string(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    search: str = typer.Option(..., help="string to search"),
    replace: str = typer.Option(..., help="replacement string"),
    run: bool = typer.Option(False, help="run the command"),
    shuffle_preview: bool = typer.Option(True, help="shuffle preview"),
):
    db = DBManager(db_path)
    conversations = db.all_conversations()
    logger.info("Preview first 5 conversations:")
    max_preview = 5
    preview_count = 0

    matched_conversations = []
    if shuffle_preview:
        random.shuffle(conversations)
    for c in track(conversations):
        matched = False
        matched_messages = []

        if search in c.data["name"]:
            matched = True
            if preview_count < max_preview:
                matched_messages.append(c.data["name"])

        if search in c.data["prompt"]:
            matched = True
            if preview_count < max_preview:
                matched_messages.append(c.data["prompt"])

        for m in c.data["messages"]:
            if search in m["content"]:
                matched = True
                if preview_count < max_preview:
                    matched_messages.append(m["content"])

        if matched:
            preview_count += 1

            if preview_count < max_preview:
                print(f"Search Result-{preview_count}".center(100, "-"))
                print("[bold red]Original Data[/bold red]")
                print(matched_messages)
                print("[bold green]Replaced Data[/bold green]")
                modified_messages = [
                    _.replace(search, replace) for _ in matched_messages
                ]
                print(modified_messages)

            matched_conversations.append(c)

    logger.info(
        f"Total conversations {db.count_conversations()}, contains [{search}]: {len(matched_conversations)}"
    )

    if run:
        for it in track(matched_conversations, description="replacing string"):
            it.data["name"] = it.data["name"].replace(search, replace)
            it.data["prompt"] = it.data["prompt"].replace(search, replace)
            for m in it.data["messages"]:
                m["content"] = m["content"].replace(search, replace)
            it.updated_at = datetime.utcnow()
            db.update_conversation(it)
        db.vacuum()


@typer_app.command(help="Language Classification")
def classify_lang(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
):
    from llm_labeling_ui.lang_classification import LanguageClassifier

    lang_classifier = LanguageClassifier()
    db = DBManager(db_path)
    conversions_count = db.count_conversations()
    logger.info(f"Total conversations: {conversions_count}")
    page_size = 256
    total_pages = math.ceil(conversions_count / page_size)
    for page in track(range(total_pages)):
        convs = db.get_conversations(page=page, page_size=page_size)
        for conv in convs:
            if conv.data.get("lang"):
                continue
            lang = lang_classifier(conv.merged_text())
            conv.data["lang"] = lang
        db.bucket_update_conversation([it.dict() for it in convs])


@typer_app.command(help="Create embedding")
def create_embedding(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    save_path: Path = typer.Option(
        None,
        dir_okay=False,
        help="Parquet file with column name: id, embedding. If None, embedding will be saved in the same directory as db_path, with parquet file suffix.",
    ),
    model_id: str = typer.Option("BAAI/bge-small-zh-v1.5"),
    device: str = typer.Option("cpu"),
):
    if save_path is None:
        save_path = db_path.with_suffix(".parquet")

    from llm_labeling_ui.embedding import EmbeddingModel
    import pandas as pd

    db = DBManager(db_path)
    model = EmbeddingModel(model_id, device)

    if save_path.exists():
        exists_df = pd.read_parquet(save_path)
        logger.info(f"Load exists embedding: {len(exists_df)}")
    else:
        exists_df = None

    res = []
    total = db.count_conversations()
    logger.info(f"Total conversations: {total}")
    page_size = 256
    for convs in track(
        db.gen_conversations(page_size), total=math.ceil(total / page_size)
    ):
        for conv in convs:
            if exists_df is not None:
                if str(conv.id) in exists_df["id"].values:
                    continue
            vector = model(conv.merged_text())
            res.append({"id": str(conv.id), "embedding": vector})

    df = pd.DataFrame(res)
    if exists_df is not None:
        logger.info(f"df ({len(df)})")
        df = pd.concat([exists_df, df], ignore_index=True)
        logger.info(f"Merge result: {len(df)}")

    df.to_parquet(save_path)


@typer_app.command(help="DBSCAN embedding cluster")
def cluster_embedding(
    embedding: Path = typer.Option(
        ...,
        exists=True,
        dir_okay=False,
        help="Parquet file with column name: id, embedding.",
    ),
    save_path: Path = typer.Option(
        None,
        exists=False,
        dir_okay=False,
        help="If None, cluster result will be saved in the same directory as parquet file",
    ),
    force: bool = typer.Option(False, help="Force to run clustering"),
    eps: float = typer.Option(0.2, help="DBSCAN eps"),
    min_samples: int = typer.Option(3, help="DBSCAN min_samples"),
    max_samples: int = typer.Option(
        20,
        help="If the number of samples in a cluster exceeds max_samples, multiply eps by 2/3 and cluster again.",
    ),
    epochs: int = typer.Option(5, help="Number of times all data is clustered."),
    bucket_size: int = typer.Option(
        20000, help="The maximum amount of data for a single cluster"
    ),
):
    import pandas as pd
    from llm_labeling_ui.cluster_dedup import run_dbscan_cluster

    if save_path is None:
        save_path = embedding.with_suffix(".cluster.json")
    if save_path.exists():
        if not force:
            logger.error(
                f"Cluster result exists: {save_path}, use --force to overwrite."
            )
            return
        else:
            logger.warning(f"Force to run clustering, save result to {save_path}")

    logger.info(f"Save cluster result to {save_path}")

    df = pd.read_parquet(embedding)
    id_groups = run_dbscan_cluster(
        df, eps, min_samples, max_samples, epochs, bucket_size
    )
    logger.info(
        f"Total samples: {len(df)}, cluster group count: {len(id_groups)}, samples in clusters: {sum([len(it) for it in id_groups])}"
    )
    with open(save_path, "w", encoding="utf-8") as fw:
        json.dump(
            {
                "groups": id_groups,
                "meta": {
                    "eps": eps,
                    "min_samples": min_samples,
                    "max_samples": max_samples,
                    "epochs": epochs,
                    "bucket_size": bucket_size,
                },
            },
            fw,
            ensure_ascii=False,
            indent=2,
        )


@typer_app.command(help="View cluster result")
def view_cluster(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    cluster_path: Path = typer.Option(..., exists=True, dir_okay=False),
):
    with open(cluster_path, "r", encoding="utf-8") as fr:
        cluster_result = json.load(fr)
    id_groups: List[List[str]] = cluster_result["groups"]
    id_groups.sort(key=lambda it: len(it), reverse=True)

    db = DBManager(db_path)
    index = 0
    while True:
        group = id_groups[index]
        convs = db.get_conversations_by_ids(group)
        for conv_i, conv in enumerate(convs):
            print(
                f"conv{conv_i}-message-count:{len(conv.data['messages'])}".center(
                    80, "-"
                )
            )
            print(conv.merged_text(max_messages=1))
        choice = Prompt.ask(
            f"group: {index}/{len(id_groups)}",
            choices=["h", "l", "n", "r"],
            default="l",
        )
        if choice == "h":
            index -= 1
            if index < 0:
                index = len(id_groups) - 1
        elif choice == "l":
            index += 1
            if index >= len(id_groups):
                index = 0
        elif choice == "r":
            random_index = random.randint(0, len(id_groups) - 1)
            index = random_index
        elif choice == "n":
            break


if __name__ == "__main__":
    typer_app()
