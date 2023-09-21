from pathlib import Path

import fasttext
from typing import Tuple

CURRENT_DIR = Path(__file__).absolute().parent


class LanguageClassifier:
    def __init__(self):
        pretrained_lang_model = str(CURRENT_DIR / "lid.176.ftz")
        self.model = fasttext.load_model(pretrained_lang_model)

    def __call__(self, text: str) -> str:
        # remove all symbols
        text = text[:512].replace("\n", "")
        predictions = self.model.predict(text, k=1)
        score = predictions[1][0]
        pred = predictions[0][0].replace("__label__", "")
        return pred
