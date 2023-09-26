import math
from pathlib import Path

from loguru import logger
import typer
from rich.progress import track

from llm_labeling_ui.db_schema import DBManager

app = typer.Typer(
    add_completion=False,
    pretty_exceptions_show_locals=False,
    short_help="Add tags to you data, such as lang classification(en,zh..), traditional or simplified chinese classification, etc.",
)


@app.command(help="Language Classification")
def lang(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
):
    from llm_labeling_ui.lang_classification import LanguageClassifier

    lang_classifier = LanguageClassifier()
    db = DBManager(db_path)
    conversions_count = db.count_conversations()
    logger.info(f"Total conversations: {conversions_count}")
    page_size = 256
    total_pages = math.ceil(conversions_count / page_size)
    for convs in track(db.gen_conversations(batch_size=page_size), total=total_pages):
        for conv in convs:
            tags = conv.data.get("tags", {})
            if tags.get("lang"):
                continue
            lang = lang_classifier(conv.merged_text())
            conv.data["tags"] = {**tags, "lang": lang}
        db.bucket_update_conversation([it.dict() for it in convs])


@app.command(help="Traditional or Simplified Chinese Classification")
def is_traditional_zh(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
):
    import opencc

    converter = opencc.OpenCC("t2s.json")

    def is_traditional_chinese(text):
        converted_text = converter.convert(text)
        if converted_text != text:
            return True
        return False

    db = DBManager(db_path)
    conversions_count = db.count_conversations()
    logger.info(f"Total conversations: {conversions_count}")
    page_size = 256
    total_pages = math.ceil(conversions_count / page_size)

    is_traditional_count = 0
    for convs in track(db.gen_conversations(batch_size=page_size), total=total_pages):
        for conv in convs:
            tags = conv.data.get("tags", {})
            is_traditional = is_traditional_chinese(conv.merged_text(role="user"))
            if is_traditional:
                is_traditional_count += 1
            conv.data["tags"] = {
                **tags,
                "is_traditional_zh": is_traditional,
            }
        db.bucket_update_conversation([it.dict() for it in convs])
    logger.info(f"Total traditional chinese conversations: {is_traditional_count}")
