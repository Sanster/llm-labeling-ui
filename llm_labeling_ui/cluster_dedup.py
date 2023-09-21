import math
from typing import List
import pandas as pd
import numpy as np
from loguru import logger
from sklearn.cluster import DBSCAN
from more_itertools import flatten


def _inter_run_dbscan_cluster(
    df: pd.DataFrame,
    eps: float,
    min_samples: int,
    max_samples: int,
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
        clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
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
        logger.info(f"Processing bucket {i + 1}/{total_buckets}")
        index_groups = predict(bucket["embedding"], eps)
        logger.info(
            f"bucket groups: {len(index_groups)}. {sorted([len(it) for it in index_groups], reverse=True)}"
        )
        for index_group in index_groups:
            id_group = bucket.iloc[index_group].id.tolist()
            if len(id_group) <= max_samples:
                all_id_groups.append(id_group)
            else:
                large_sub_bucket = bucket[bucket["id"].isin(id_group)]
                sub_index_groups = predict(large_sub_bucket["embedding"], eps=eps / 2)
                sub_id_groups = [
                    large_sub_bucket.iloc[sub_index_group].id.tolist()
                    for sub_index_group in sub_index_groups
                ]
                logger.info(
                    f"Group size: {len(large_sub_bucket)} > max_samples({max_samples}), recluster -> {len(sub_id_groups)} sub groups: {[len(it) for it in sub_id_groups]}"
                )
                for it in sub_id_groups:
                    if len(it) <= max_samples:
                        all_id_groups.append(it)
    return all_id_groups


def run_dbscan_cluster(
    df: pd.DataFrame,
    eps: float,
    min_samples: int,
    max_samples: int,
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
        logger.info(
            f"Running DBSCAN clustering epoch: {iter + 1}/{epochs}, total samples: {len(df)}"
        )
        id_groups = _inter_run_dbscan_cluster(
            df, eps, min_samples, max_samples, bucket_size
        )
        clustered_ids = set(flatten(id_groups))
        unclustered_ids = set(df.id.tolist()) - clustered_ids
        df = df[df.id.isin(unclustered_ids)]
        df = df.sample(frac=1)
        all_id_groups.extend(id_groups)

    return all_id_groups
