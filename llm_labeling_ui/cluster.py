import math
from typing import List
import pandas as pd
import numpy as np
from loguru import logger
from sklearn.cluster import DBSCAN, OPTICS
from more_itertools import flatten
from transformers import AutoTokenizer, AutoModel
import torch


def _inter_run_dbscan_cluster(
    df: pd.DataFrame,
    metric: str,
    eps: float,
    min_samples: int,
    max_samples: int,
    recluster_samples: int,
    bucket_size: int,
) -> List[List[str]]:
    """
    Run DBSCAN clustering on a dataframe's embedding column.

    Args:
        df:
        eps: DBSCAN eps. The maximum distance between two samples for one to be considered
            as in the neighborhood of the other.
        min_samples:
        max_samples: If the number of samples in a cluster exceeds max_samples, multiply eps by 2/3 and cluster again.
        bucket_size: The maximum amount of data for a single cluster

    Returns: The returned clustering results, the data of each group is between [min_samples, max_samples].
    """

    def predict(X, eps) -> List[List[int]]:
        # metric = "euclidean"
        # metric = "cosine"
        clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric=metric)
        # clusterer = OPTICS(
        #     min_samples=min_samples,
        #     max_eps=eps,
        #     metric=metric,
        #     cluster_method="dbscan",
        # ).fit(X.tolist())
        y_db = clusterer.fit_predict(X.tolist())

        unique_labels = np.unique(y_db)
        res = []
        for label in unique_labels:
            if label == -1:
                continue
            indexes = np.where(y_db == label)[0]
            res.append(indexes.tolist())
        return res

    total_buckets = math.ceil(len(df) / bucket_size)
    all_id_groups: List[List[str]] = []
    for i, bucket in enumerate(np.array_split(df, total_buckets)):
        logger.info(f"Processing bucket {i + 1}/{total_buckets}, size: {len(bucket)}")
        index_groups = predict(bucket["embedding"], eps)
        logger.info(
            f"bucket groups: {len(index_groups)}. {sorted([len(it) for it in index_groups], reverse=True)}"
        )
        for index_group in index_groups:
            id_group = bucket.iloc[index_group].id.tolist()
            if len(id_group) <= max_samples:
                all_id_groups.append(id_group)
            elif len(id_group) >= recluster_samples:
                large_sub_bucket = bucket[bucket["id"].isin(id_group)]
                sub_index_groups = predict(
                    large_sub_bucket["embedding"], eps=eps * 4 / 5
                )
                sub_id_groups = [
                    large_sub_bucket.iloc[sub_index_group].id.tolist()
                    for sub_index_group in sub_index_groups
                ]
                if len(sub_id_groups):
                    logger.info(
                        f"Group size: {len(large_sub_bucket)} > recluster_samples({recluster_samples}), recluster {len(sub_id_groups)} sub groups: {[len(it) for it in sub_id_groups]}"
                    )
                for it in sub_id_groups:
                    if len(it) <= max_samples:
                        all_id_groups.append(it)
    return all_id_groups


def run_dbscan_cluster(
    df: pd.DataFrame,
    metric: str,
    eps: float,
    eps_decay: float,
    min_samples: int,
    max_samples: int,
    recluster_samples: int,
    epochs: int,
    bucket_size: int,
) -> List[List[str]]:
    """
    Run DBSCAN clustering on a dataframe's embedding column.

    Args:
        df:
        eps: DBSCAN eps. The maximum distance between two samples for one to be considered
            as in the neighborhood of the other.
        min_samples:
        max_samples: If the number of samples in a cluster exceeds max_samples, multiply eps by 0.5 and cluster again.
        epochs: Number of times all data is clustered.
        bucket_size: The maximum amount of data for a single cluster

    Returns: The returned clustering results, the data of each group is between [min_samples, max_samples].
    """
    all_id_groups: List[List[str]] = []
    for iter in range(epochs):
        total_samples_count = len(df)
        logger.info(
            f"Running DBSCAN clustering epoch: {iter + 1}/{epochs}, total samples: {total_samples_count}"
        )
        id_groups = _inter_run_dbscan_cluster(
            df, metric, eps, min_samples, max_samples, recluster_samples, bucket_size
        )
        new_eps = eps * eps_decay
        logger.info(f"Decay eps: {eps} -> {new_eps}")
        eps = new_eps
        clustered_ids = set(flatten(id_groups))
        unclustered_ids = set(df.id.tolist()) - clustered_ids
        df = df[df.id.isin(unclustered_ids)]
        df = df.sample(frac=1)
        all_id_groups.extend(id_groups)
        if len(df) == total_samples_count:
            logger.warning(f"DBSCAN clustering early stop at epoch: {iter + 1}")
            break

    return all_id_groups


# Sentences we want sentence embeddings for
class EmbeddingModel:
    def __init__(self, model_id, device):
        # Load model from HuggingFace Hub
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id).eval().to(device)
        self.device = device

    @torch.inference_mode()
    def __call__(self, text: str) -> List[float]:
        # Tokenize sentences
        encoded_input = self.tokenizer(
            [text], padding=True, truncation=True, return_tensors="pt"
        )
        # for s2p(short query to long passage) retrieval task, add an instruction to query (not add instruction for passages)
        # encoded_input = tokenizer([instruction + q for q in queries], padding=True, truncation=True, return_tensors='pt')

        encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}

        # Compute token embeddings
        model_output = self.model(**encoded_input)
        # Perform pooling. In this case, cls pooling.
        sentence_embeddings = model_output[0][:, 0]
        # normalize embeddings
        sentence_embeddings = torch.nn.functional.normalize(
            sentence_embeddings, p=2, dim=1
        )
        return sentence_embeddings.cpu().tolist()[0]
