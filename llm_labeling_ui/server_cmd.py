import os
from pathlib import Path

import typer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gunicorn.app.base import BaseApplication
from loguru import logger
import typer

from llm_labeling_ui.db_schema import DBManager
from llm_labeling_ui.schema import Config

app = typer.Typer(
    add_completion=False,
    pretty_exceptions_show_locals=False,
    short_help="Start the web server",
)

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


@app.command(help="Start the web server")
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
