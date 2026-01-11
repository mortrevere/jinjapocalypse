import random
import yaml
import unicodedata
import re
from loguru import logger
import json
import plugin

class Tokens:
    def __init__(self):
        self.run_id = random.randint(4, 42)
        self.token_tmpl = f"[--- JNJPCLPS{self.run_id} -- ()]"

    def bake(self, parameters):
        baked = self.token_tmpl.replace("()", f"{json.dumps(parameters)}")
        logger.info(baked)
        return baked


_TOKENS = Tokens()


class Toolbox:
    @staticmethod
    def hourri():
        return "\\o/"

    def load_yaml(path):
        path = "src/" + path
        with open(path) as f:
            data = yaml.safe_load(f)
            return data

    def get_dot_path(data, dot_path):
        value = data
        for chunk in dot_path.split("."):
            value = value.get(chunk, {})
        return value

    def uniq(data, key):
        _set = set()
        for item in data:
            try:
                for _item in Toolbox.get_dot_path(item, key):
                    _set.add(_item)
            except Exception:
                ...
        return list(_set)

    def lookup(data, key, default=None):
        if default is None:
            default = key
        return data.get(key, default)

    def slugify(text, delimiter="-"):
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"[-\s]+", delimiter, re.sub(r"[^\w\s-]", "", text).strip().lower())

    def start_page(page_name):
        page_name = Toolbox.slugify(page_name)
        p = {"type": "start_page", "page_name": page_name}
        return _TOKENS.bake(p)

    def end_page():
        p = {"type": "end_page"}
        return _TOKENS.bake(p)
    
    def __init__(self):
        self.plugins = {}

        for cls in plugin.Plugin.__subclasses__():
            ns = getattr(cls, "namespace", None)
            if ns:
                inst = cls()
                self.plugins[ns] = inst
                setattr(self, ns, inst)
