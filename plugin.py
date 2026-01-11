from loguru import logger
import sys
import os
import requests

class Plugin():
    namespace = ""

    @property
    def name(self):
        return self.__class__.__name__

    def __init__(self):
        if not self.namespace:
            logger.critical(f"Plugin {self.name} doesn't declare a namespace")
            sys.exit(1)


class Notion(Plugin):
    namespace = "notion"
    api_key = os.environ.get("NOTION_API_KEY")

    def __init__(self):
        super().__init__()
        if not self.api_key:
            logger.critical(f"Missing NOTION_API_KEY in env")
            sys.exit(1)

    def get_block(self, block_id):  # works with page id too
        url = f"https://api.notion.com/v1/blocks/{block_id}/children"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return data
    
    def _plain_text(self, rich_text):
        return rich_text.get("plain_text", "")
    
    def todo_list(self, notion_response, include_checked=False):
        results = notion_response.get("results", [])
        output = []

        for block in results:
            if block.get("type") != "to_do":
                continue
            todo = block.get("to_do", {})
            if include_checked and todo.get("checked"):
                continue
            for rt in todo.get("rich_text", []):
                output.append(self._plain_text(rt))
        return output

    def todo_list_from_page(self, page_id):
        return self.todo_list(self.get_block(page_id))