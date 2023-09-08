import os
from typer import Typer

from gunicorn.app.base import BaseApplication
import typer
from schema import Config


typer_app = Typer(add_completion=False, pretty_exceptions_show_locals=False)

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


class StandaloneApplication(BaseApplication):
    def __init__(self, app, options, config):
        self.options = options or {}
        self.app = app
        self.config = config
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

    api = Api(worker.app.app, worker.app.config)
    api.app.include_router(api.router)


@typer_app.command()
def main(
    host: str = typer.Option("0.0.0.0"),
    port: int = typer.Option(8000),
):
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
    StandaloneApplication(app_factory(), options, config).run()


if __name__ == "__main__":
    typer_app()
