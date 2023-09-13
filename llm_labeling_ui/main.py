import os
from datetime import datetime
from pathlib import Path
from typing import List

import typer
from gunicorn.app.base import BaseApplication
from loguru import logger
from typer import Typer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm_labeling_ui.db_schema import DBManager
from llm_labeling_ui.schema import Config

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
    history_file: Path = typer.Option(None, dir_okay=False),
    db_path: Path = typer.Option(None, dir_okay=False),
    tokenizer: str = typer.Option(None),
):
    assert (
        history_file is not None or db_path is not None
    ), "one of history_file or db_path must be set"

    assert not (
        history_file is not None and db_path is not None
    ), "only one of history_file or db_path can be set"

    config = Config(web_app_dir=web_app_dir)
    options = {
        "bind": f"{host}:{port}",
        # 'workers': workers,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "timeout": 120,
        "post_worker_init": post_worker_init,
        "capture_output": True,
    }

    db_path = history_file.with_suffix(".sqlite")
    if not db_path.exists():
        logger.info(f"create db at {db_path}")
        db = DBManager(db_path)
        db = db.create_from_json_file(history_file)
    else:
        logger.warning(
            f"loading db from {db_path}, data may be different from {history_file}"
        )
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


if __name__ == "__main__":
    typer_app()
