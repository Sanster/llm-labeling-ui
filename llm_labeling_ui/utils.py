import distutils
import random
import typing
from typing import Any, Dict, List, Union

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

if typing.TYPE_CHECKING:
    from llm_labeling_ui.db_schema import Conversation

MESSAGE_FILTER_NONE = "message-count-none"
MESSAGE_FILTER_EQUAL = "message-count-equal"
MESSAGE_FILTER_GREATER = "message-count-greater"
MESSAGE_FILTER_LESS = "message-count-less"


def interactive_view_conversations(
    db, id_groups: Union[List[List[str]], List["Conversation"]], max_messages=-1
):
    if len(id_groups) == 0:
        return
    if not isinstance(id_groups[0], list):
        id_groups = [[str(c.id)] for c in id_groups]
    index = 0

    console = Console()
    while True:
        group = id_groups[index]
        conversations = db.get_conversations_by_ids(group)

        markdown_str = ""
        for conv_i, conv in enumerate(conversations):
            markdown_str += f"# {index}-{conv_i}/{len(id_groups)} message count {len(conv.data['messages'])}\n\n"
            if max_messages == -1:
                max_messages = len(conv.data["messages"])
            for m in conv.data["messages"][0:max_messages]:
                markdown_str += f"## {m['role']}\n\n{m['content']}\n\n"

        md = Markdown(markdown_str)
        console.print(md)

        choice = Prompt.ask(
            f"{index}/{len(id_groups)}",
            choices=["h", "l", "r", "q"],
            default="l",
        )
        if choice == "h":
            index -= 1
            if index < 0:
                index = len(id_groups) - 1
        elif choice == "l":
            index += 1
            if index >= len(id_groups):
                index = 0
        elif choice == "r":
            random_index = random.randint(0, len(id_groups) - 1)
            index = random_index
        elif choice == "q":
            break


def str_to_bool(text) -> bool:
    try:
        return bool(distutils.util.strtobool(text))
    except:
        return text


def parse_tag(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    splits = text.split(",")
    if len(splits) % 2 != 0:
        raise ValueError(f"Invalid tag {text}, please use key1,value1,key2,value2,...")

    tags = {}
    for i in range(0, len(splits), 2):
        tags[splits[i]] = str_to_bool(splits[i + 1])
    return tags
