from datetime import datetime
from pathlib import Path

import typer
from loguru import logger
from rich.progress import track
from typer import Typer

from llm_labeling_ui.cluster_cmd import app as cluster_app
from llm_labeling_ui.conversation_cmd import app as conversation_app
from llm_labeling_ui.server_cmd import app as server_app
from llm_labeling_ui.tag_cmd import app as tag_app
from llm_labeling_ui.db_schema import DBManager
from llm_labeling_ui.utils import parse_tag

typer_app = Typer(add_completion=False, pretty_exceptions_show_locals=False)
typer_app.add_typer(cluster_app, name="cluster")
typer_app.add_typer(conversation_app, name="conversation")
typer_app.add_typer(tag_app, name="tag")
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
    tag: str = typer.Option(
        "", help="tag to filter conversations. key1,value1,key2,value2..."
    ),
    min_messages: int = typer.Option(0, help="min messages count. included"),
    max_messages: int = typer.Option(10000, help="max messages count. excluded"),
    count: int = typer.Option(-1, help="max conversations to export. -1 for all."),
    force: bool = typer.Option(False, help="force overwrite save_path if exists"),
):
    tags = parse_tag(tag)

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
        save_path,
        count,
        min_messages=min_messages,
        max_messages=max_messages,
        tags=tags,
    )


if __name__ == "__main__":
    typer_app()
