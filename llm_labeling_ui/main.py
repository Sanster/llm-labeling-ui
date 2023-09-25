import math
from datetime import datetime
from pathlib import Path

import typer
from loguru import logger
from rich.progress import track
from typer import Typer

from llm_labeling_ui.cluster_cmd import app as cluster_app
from llm_labeling_ui.conversation_cmd import app as conversation_app
from llm_labeling_ui.server_cmd import app as server_app
from llm_labeling_ui.db_schema import DBManager

typer_app = Typer(add_completion=False, pretty_exceptions_show_locals=False)
typer_app.add_typer(cluster_app, name="cluster")
typer_app.add_typer(conversation_app, name="conversation")
typer_app.add_typer(server_app, name="server")


@typer_app.command(help="Create db from chatbot-ui history file")
def create_db(
    json_path: Path = typer.Option(
        ..., exists=True, dir_okay=False, help="chatbotui json history file"
    ),
    save_path: Path = typer.Option(None, dir_okay=False),
    force: bool = typer.Option(False, help="force overwrite save_path if exists"),
):
    if save_path is None:
        save_path = json_path.with_suffix(".sqlite")
    logger.info(f"create db at {save_path}")
    if save_path.exists():
        if not force:
            raise FileExistsError(f"{save_path} exists, use --force to overwrite")

    db = DBManager(save_path)
    db.create_from_json_file(json_path)


@typer_app.command(help="Export db to chatbot-ui history file")
def export(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    save_path: Path = typer.Option(
        None,
        dir_okay=False,
        help="If not specified, it will be generated in the same directory as db_path, and the file name will be added with a timestamp.",
    ),
    min_messages: int = typer.Option(0, help="min messages count. included"),
    max_messages: int = typer.Option(10000, help="max messages count. excluded"),
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
    db.export_to_json_file(
        save_path, min_messages=min_messages, max_messages=max_messages
    )


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


if __name__ == "__main__":
    typer_app()
