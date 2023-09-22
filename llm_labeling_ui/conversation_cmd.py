from datetime import datetime
from typing import List

import typer
from pathlib import Path

from loguru import logger
from rich.progress import track

from llm_labeling_ui.db_schema import DBManager, Conversation
from llm_labeling_ui.utils import interactive_view_conversations

app = typer.Typer(
    add_completion=False,
    pretty_exceptions_show_locals=False,
    short_help="Conversation operations, such as remove prefix, remove duplicate, etc.",
)


@app.command(help="Remove conversation which is prefix of another conversation")
def remove_prefix(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = [Conversation(**it.data) for it in db.all_conversations()]
    logger.info(f"Total conversations: {len(conversations)}")

    import pygtrie

    trie = pygtrie.CharTrie()

    prefix_conversation_to_remove = []
    for it in track(conversations, description="building trie"):
        trie[it.merged_text()] = True

    for it in track(conversations, description="checking prefix"):
        if trie.has_subtrie(it.merged_text()):
            # 完全相等的 text 不会有 subtrie
            prefix_conversation_to_remove.append(it)

    logger.info(f"Found {len(prefix_conversation_to_remove)} prefix conversation")

    if run:
        for it in track(prefix_conversation_to_remove, description="removing"):
            db.delete_conversation(it.id)
        db.vacuum()


@app.command(help="Remove duplicate conversation only keep one of them")
def remove_duplicate(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = [Conversation(**it.data) for it in db.all_conversations()]
    logger.info(f"Total conversations: {len(conversations)}")

    conversation_to_remove = []
    merged_conversations = set()
    for it in track(conversations, description="finding duplicate"):
        merged_text = it.merged_text()
        if merged_text in merged_conversations:
            conversation_to_remove.append(it)
        else:
            merged_conversations.add(merged_text)

    logger.info(f"Found {len(conversation_to_remove)} duplicate conversation")

    if run:
        for it in track(conversation_to_remove, description="removing duplicates"):
            db.delete_conversation(it.id)
        db.vacuum()


@app.command(help="View conversation contain certain strings")
def view(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    search: List[str] = typer.Option([""], help="string to search"),
):
    db = DBManager(db_path)
    conversations = db.all_conversations(search_term=search)
    logger.info(f"Total conversations: {len(conversations)}")
    interactive_view_conversations(db, conversations, max_messages=5)


@app.command(help="Delete conversation contain certain string")
def delete(
    db_path: Path = typer.Option(..., exists=True, dir_okay=False),
    search: str = typer.Option(..., help="string to search"),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = db.all_conversations()
    logger.info(f"Total conversations: {len(conversations)}")

    conversation_to_remove = []
    for it in track(conversations, description="finding duplicate"):
        merged_text = it.merged_text()
        if search in merged_text:
            conversation_to_remove.append(it)

    logger.info(f"Found {len(conversation_to_remove)} conversations to remove")

    if run:
        for it in track(conversation_to_remove, description="removing conversations"):
            db.delete_conversation(it.id)
        db.vacuum()
    else:
        interactive_view_conversations(db, conversation_to_remove, max_messages=5)


@app.command(help="Delete string in conversation")
def delete_string(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    string: str = typer.Option(None, help="string to delete"),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = db.all_conversations(search_term=string)
    logger.info(
        f"Total conversations {db.count_conversations()}, contains [{string}]: {len(conversations)}"
    )

    if run:
        for it in track(conversations, description="delete string"):
            it.data["prompt"] = it.data["prompt"].replace(string, "")
            for m in it.data["messages"]:
                m["content"] = m["content"].replace(string, "")
            it.updated_at = datetime.utcnow()
            db.update_conversation(it)
        db.vacuum()
    else:
        interactive_view_conversations(db, conversations, max_messages=5)


@app.command(help="Replace string in conversation")
def replace_string(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False),
    search: str = typer.Option(..., help="string to search"),
    replace: str = typer.Option(..., help="replacement string"),
    run: bool = typer.Option(False, help="run the command"),
):
    db = DBManager(db_path)
    conversations = db.all_conversations()
    logger.info("Preview first 5 conversations:")
    max_preview = 5
    preview_count = 0

    matched_conversations = []
    for c in track(conversations):
        matched = False
        matched_messages = []

        if search in c.data["name"]:
            matched = True
            if preview_count < max_preview:
                matched_messages.append(c.data["name"])

        if search in c.data["prompt"]:
            matched = True
            if preview_count < max_preview:
                matched_messages.append(c.data["prompt"])

        for m in c.data["messages"]:
            if search in m["content"]:
                matched = True
                if preview_count < max_preview:
                    matched_messages.append(m["content"])

        if matched:
            preview_count += 1

            if preview_count < max_preview:
                print(f"Search Result-{preview_count}".center(100, "-"))
                print("[bold red]Original Data[/bold red]")
                print(matched_messages)
                print("[bold green]Replaced Data[/bold green]")
                modified_messages = [
                    _.replace(search, replace) for _ in matched_messages
                ]
                print(modified_messages)

            matched_conversations.append(c)

    logger.info(
        f"Total conversations {db.count_conversations()}, contains [{search}]: {len(matched_conversations)}"
    )

    if run:
        for it in track(matched_conversations, description="replacing string"):
            it.data["name"] = it.data["name"].replace(search, replace)
            it.data["prompt"] = it.data["prompt"].replace(search, replace)
            for m in it.data["messages"]:
                m["content"] = m["content"].replace(search, replace)
            it.updated_at = datetime.utcnow()
            db.update_conversation(it)
        db.vacuum()
    else:
        interactive_view_conversations(db, matched_conversations)
