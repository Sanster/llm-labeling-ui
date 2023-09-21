from typing import List
from transformers import AutoTokenizer, AutoModel
import torch


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
