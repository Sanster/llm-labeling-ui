from enum import Enum
import json
import math
import random
from typing import List
from more_itertools import flatten

import typer
from pathlib import Path

from loguru import logger
from rich.progress import track
from rich.prompt import Confirm
from rich import print
from rich.markdown import Markdown

from llm_labeling_ui.db_schema import DBManager
from llm_labeling_ui.utils import interactive_view_conversations

app = typer.Typer(
    add_completion=False,
    pretty_exceptions_show_locals=False,
    short_help="Cluster operations, such as create embedding, run cluster, dedup, etc.",
)


@app.command(help="Create embedding")
def create_embedding(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    save_path: Path = typer.Option(
        None,
        dir_okay=False,
        help="Parquet file with column name: id, embedding. If None, embedding will be saved in the same directory as db_path, with parquet file suffix.",
    ),
    model_id: str = typer.Option("BAAI/bge-base-zh-v1.5"),
    max_messages: int = typer.Option(
        1, help="Number of messages used to create embedding. -1 means all messages."
    ),
    device: str = typer.Option("cpu"),
):
    if save_path is None:
        save_path = db_path.with_suffix(".parquet")

    from llm_labeling_ui.cluster import EmbeddingModel
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
            vector = model(conv.merged_text(max_messages=max_messages))
            res.append({"id": str(conv.id), "embedding": vector})

    df = pd.DataFrame(res)
    if exists_df is not None:
        logger.info(f"df ({len(df)})")
        df = pd.concat([exists_df, df], ignore_index=True)
        logger.info(f"Merge result: {len(df)}")

    df.to_parquet(save_path)


class DBSCANMetric(str, Enum):
    euclidean = "euclidean"
    cosine = "cosine"
    manhattan = "manhattan"


@app.command(help="DBSCAN embedding cluster")
def run(
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
    resume: bool = typer.Option(False, help="Resume cluster result"),
    metric: DBSCANMetric = typer.Option(
        "euclidean", help="DBSCAN metric. euclidean or cosine"
    ),
    eps: float = typer.Option(0.5, help="DBSCAN eps"),
    eps_decay: float = typer.Option(
        0.995, help="DBSCAN eps decay on every epoch. new_eps = eps * eps_decay"
    ),
    min_samples: int = typer.Option(3, help="DBSCAN min_samples"),
    max_samples: int = typer.Option(
        10,
        help="max samples to keep in a cluster",
    ),
    recluster_samples: int = typer.Option(
        80,
        help="If the number of samples in a cluster exceeds recluster_samples, reduce eps cluster again.",
    ),
    epochs: int = typer.Option(5, help="Number of times all data is clustered."),
    bucket_size: int = typer.Option(
        20000, help="The maximum amount of data for a single cluster"
    ),
):
    import pandas as pd
    from llm_labeling_ui.cluster import run_dbscan_cluster

    if save_path is None:
        save_path = embedding.with_suffix(".cluster.json")

    exist_groups = []
    if save_path.exists():
        assert not (
            force and resume
        ), "Cannot use --force and --resume at the same time"

        if force:
            logger.warning(f"Force to run clustering, save result to {save_path}")
        elif resume:
            logger.warning(f"Resume clustering, save result to {save_path}")

            with open(save_path, "r", encoding="utf-8") as fr:
                exist_groups = json.load(fr)["groups"]
        else:
            logger.error(
                f"Cluster result exists: {save_path}, use --force to overwrite or --resume to resume"
            )
            return

    logger.info(f"Save cluster result to {save_path}")

    df = pd.read_parquet(embedding)
    total_samples_count = len(df)
    flatten_exists_groups = set(flatten(exist_groups))
    logger.info(f"Total samples: {total_samples_count}")
    if len(flatten_exists_groups) > 0:
        df = df[~df.id.isin(flatten_exists_groups)]
        logger.info(
            f"Remove {len(flatten_exists_groups)} embedding in exists groups, remain: {len(df)}"
        )

    logger.info(f"Embedding size: {len(df['embedding'].iloc[0])}")
    id_groups = run_dbscan_cluster(
        df,
        metric,
        eps,
        eps_decay,
        min_samples,
        max_samples,
        recluster_samples,
        epochs,
        bucket_size,
    )
    id_groups.extend(exist_groups)
    logger.info(
        f"Total samples: {total_samples_count}, cluster group count: {len(id_groups)}, samples in clusters: {sum([len(it) for it in id_groups])}"
    )
    with open(save_path, "w", encoding="utf-8") as fw:
        json.dump(
            {
                "groups": id_groups,
                "meta": {
                    "eps": eps,
                    "min_samples": min_samples,
                    "max_samples": max_samples,
                    "recluster_samples": recluster_samples,
                    "epochs": epochs,
                    "bucket_size": bucket_size,
                    "total_groups": len(id_groups),
                    "total_samples_in_groups": sum([len(it) for it in id_groups]),
                },
            },
            fw,
            ensure_ascii=False,
            indent=2,
        )


@app.command(help="View cluster result")
def view(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    cluster_path: Path = typer.Option(None, dir_okay=False),
):
    if cluster_path is None:
        cluster_path = db_path.with_suffix(".cluster.json")
        logger.info(f"cluster_path is None, try to load {cluster_path}")
    if not cluster_path.exists():
        logger.error(f"cluster_path not exists: {cluster_path}")
        return

    with open(cluster_path, "r", encoding="utf-8") as fr:
        cluster_result = json.load(fr)
    id_groups: List[List[str]] = cluster_result["groups"]
    id_groups.sort(key=lambda it: len(it), reverse=True)

    db = DBManager(db_path)
    interactive_view_conversations(db, id_groups, max_messages=1)


class DedupStrategy(str, Enum):
    max_messages_count: str = "max_messages_count"
    max_messages_length: str = "max_messages_length"


@app.command(
    help="Delete redundant data in the same clustering result according to certain strategies."
)
def dedup(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    cluster_path: Path = typer.Option(None, dir_okay=False),
    cluster_keep: int = typer.Option(
        1, help="Keep the first N conversations in a cluster"
    ),
    strategy: DedupStrategy = typer.Option(
        DedupStrategy.max_messages_count, help="Dedup strategy"
    ),
    tokenizer: str = typer.Option(
        None, help="Tokenizer name. Used when strategy is max_messages_length"
    ),
    run: bool = typer.Option(False, help="Run delete"),
):
    if strategy == DedupStrategy.max_messages_length:
        assert (
            tokenizer is not None
        ), "tokenizer must be specified when strategy is max_messages_length"
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(tokenizer, trust_remote_code=True)

    if cluster_path is None:
        cluster_path = db_path.with_suffix(".cluster.json")
        logger.info(f"cluster_path is None, try to load {cluster_path}")
    if not cluster_path.exists():
        logger.error(f"cluster_path not exists: {cluster_path}")
        return

    with open(cluster_path, "r", encoding="utf-8") as fr:
        cluster_result = json.load(fr)
    id_groups: List[List[str]] = cluster_result["groups"]
    logger.info(f"Total groups: {len(id_groups)}")

    db = DBManager(db_path)
    total_conversations = db.count_conversations()
    deleted_count = 0
    if not run:
        random.shuffle(id_groups)

    for group in track(id_groups, disable=not run):
        convs = db.get_conversations_by_ids(group)
        if strategy == DedupStrategy.max_messages_count:
            convs.sort(key=lambda it: it.messages_count(), reverse=True)
        elif strategy == DedupStrategy.max_messages_length:
            convs.sort(key=lambda it: it.token_count(), reverse=True)

        convs_to_keep = convs[:cluster_keep]
        convs_to_delete = convs[cluster_keep:]
        if run:
            db.delete_conversation([it.id for it in convs_to_delete])
            deleted_count += len(convs_to_delete)
        else:
            print(Markdown(f"# Conversations to keep: ({len(convs_to_keep)})"))

            for c in convs_to_keep:
                print(Markdown(f"## Message count: {c.messages_count()}"))
                print(c.data["messages"][:2])

            print(Markdown(f"# Conversations to delete: ({len(convs_to_delete)})"))
            for c in convs_to_delete:
                print(Markdown(f"## Message count: {c.messages_count()}"))
                print(c.data["messages"][:2])

            if Confirm.ask("Press Enter to continue", default=True):
                continue
            else:
                exit(0)

    db.vacuum()
    print(
        f"Total conversations: {total_conversations}, delete {deleted_count} conversations, remain {total_conversations - deleted_count} conversations"
    )
