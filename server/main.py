import os
from pathlib import Path

import typer
from gunicorn.app.base import BaseApplication
from loguru import logger
from typer import Typer

from db_schema import DBManager
from schema import Config

typer_app = Typer(add_completion=False, pretty_exceptions_show_locals=False)

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


class StandaloneApplication(BaseApplication):
    def __init__(self, app, options, config, db):
        self.options = options or {}
        self.app = app
        self.config = config
        self.db = db
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
    from api import Api

    api = Api(worker.app.app, worker.app.config, worker.app.db)
    api.app.include_router(api.router)


@typer_app.command()
def main(
    host: str = typer.Option("0.0.0.0"),
    port: int = typer.Option(8000),
    history_file: Path = typer.Option(None, dir_okay=False),
    db_path: Path = typer.Option(None, dir_okay=False),
):
    assert (
        history_file is not None or db_path is not None
    ), "one of history_file or db_path must be set"

    assert not (
        history_file is not None and db_path is not None
    ), "only one of history_file or db_path can be set"

    # TODO: 使用 current_dir
    web_app_dir = "/Users/cwq/code/github/chatbot-ui/out"
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
        logger.info(f"loading db at {db_path}")
        db = DBManager(db_path)

    StandaloneApplication(app_factory(), options, config, db).run()


if __name__ == "__main__":
    typer_app()
