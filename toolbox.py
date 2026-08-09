import hashlib
import glob as globlib
import os
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
    GLOB_ROOTS = ("src", "media")
    GLOB_KINDS = ("all", "file", "folder")

    @staticmethod
    def hourri():
        return "\\o/"

    @staticmethod
    def _clean_project_path(path):
        path = str(path).replace("\\", "/")
        if os.path.isabs(path):
            raise ValueError("Path must be relative to the project root")
        if ".." in path.split("/"):
            raise ValueError("Path cannot contain ..")

        clean_path = os.path.normpath(path).replace("\\", "/")
        if clean_path == ".":
            raise ValueError("Path must start with src/ or media/")

        parts = clean_path.split("/")
        if len(parts) < 2 or parts[0] not in Toolbox.GLOB_ROOTS:
            raise ValueError("Path must start with src/ or media/")

        return clean_path

    @staticmethod
    def _glob_entry(path):
        project_path = path.replace("\\", "/")
        root, relative_path = project_path.split("/", 1)
        name = os.path.basename(project_path)
        stem, ext = os.path.splitext(name)
        is_file = os.path.isfile(project_path)
        is_folder = os.path.isdir(project_path)

        return {
            "path": project_path,
            "relative_path": relative_path,
            "root": root,
            "name": name,
            "stem": stem,
            "ext": ext,
            "kind": "folder" if is_folder else "file",
            "is_file": is_file,
            "is_folder": is_folder,
        }

    @staticmethod
    def glob(pattern, kind="all"):
        if kind not in Toolbox.GLOB_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(Toolbox.GLOB_KINDS)}")

        pattern = Toolbox._clean_project_path(pattern)
        matches = sorted(globlib.glob(pattern, recursive=True))
        entries = []

        for path in matches:
            clean_path = Toolbox._clean_project_path(path)
            is_file = os.path.isfile(clean_path)
            is_folder = os.path.isdir(clean_path)
            if kind == "file" and not is_file:
                continue
            if kind == "folder" and not is_folder:
                continue
            if not is_file and not is_folder:
                continue
            entries.append(Toolbox._glob_entry(clean_path))

        return entries

    @staticmethod
    def read_file(path, default=None):
        path = Toolbox._clean_project_path(path)
        if not os.path.exists(path):
            return default
        if not os.path.isfile(path):
            raise ValueError("Path must point to a file")

        with open(path, encoding="utf-8-sig") as f:
            return f.read().strip()

    @staticmethod
    def load_yaml(path):
        path = "src/" + path
        with open(path) as f:
            data = yaml.safe_load(f)
            return data

    @staticmethod
    def get_dot_path(data, dot_path):
        value = data
        for chunk in dot_path.split("."):
            value = value.get(chunk, {})
        return value

    @staticmethod
    def uniq(data, key):
        _set = set()
        for item in data:
            try:
                for _item in Toolbox.get_dot_path(item, key):
                    _set.add(_item)
            except Exception:
                ...
        return list(_set)

    @staticmethod
    def lookup(data, key, default=None):
        if default is None:
            default = key
        return data.get(key, default)

    @staticmethod
    def slugify(text, delimiter="-"):
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"[-\s]+", delimiter, re.sub(r"[^\w\s-]", "", text).strip().lower())

    @staticmethod
    def hash(text, length=None):
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return digest if length is None else digest[:length]

    @staticmethod
    def start_page(page_name):
        page_name = Toolbox.slugify(page_name)
        p = {"type": "start_page", "page_name": page_name}
        return _TOKENS.bake(p)

    @staticmethod
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
