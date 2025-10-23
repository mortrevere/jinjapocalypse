import json
import os
import random
import shutil
import yaml
from jinja2 import Environment, FileSystemLoader
from loguru import logger
import unicodedata
import re


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


class Jinjapocalypse:
    def __init__(self, src_folder="src", build_folder="build", media_folder="media"):
        self.src_folder = src_folder
        self.build_folder = build_folder
        self.media_folder = media_folder
        self.context = {"src": {}}
        self.ensure_directories_exist()

    def ensure_directories_exist(self):
        # Create directories if they do not exist and log their creation
        for folder in [self.src_folder, self.build_folder, self.media_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                logger.info(f"Created directory: {folder}")

    def render_template(self, template_path, lib_content):
        env = Environment(
            loader=FileSystemLoader(self.src_folder),
            trim_blocks=True,
            block_start_string="/o/",
            block_end_string="\\o\\",
            variable_start_string="\\o/",
            variable_end_string="\\o/",
        )

        # Prepend lib_content to the template content before rendering
        full_content = lib_content + self.context["src"][template_path]
        # Allow using plain jinja instead of hourris, nice for writing lib.ninja
        full_content = full_content.replace("{{", "\\o/")
        full_content = full_content.replace("}}", "\\o/")
        full_content = full_content.replace("{%", "/o/")
        full_content = full_content.replace("%}", "\\o\\")
        return env.from_string(full_content).render(self.context, _o_=Toolbox)

    def copy_files(self, source_folder, destination_folder):
        shutil.copytree(source_folder, destination_folder, dirs_exist_ok=True)

    def process_files(self):
        os.makedirs(self.build_folder, exist_ok=True)

        # Read lib.jinja content
        lib_jinja_path = os.path.join(self.src_folder, "lib.jinja")
        if os.path.exists(lib_jinja_path):
            with open(lib_jinja_path, "r") as lib_file:
                lib_content = lib_file.read()
        else:
            lib_content = ""
            logger.warning("lib.jinja not found. No macros will be prepended.")

        # Recursively collect all file paths under src_folder
        src_files = []
        for root, _, files in os.walk(self.src_folder):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, self.src_folder)
                if file != "lib.jinja":  # Exclude lib.jinja from the list of files to process
                    src_files.append(relative_path)

        # Read and store content of each file
        for src_file in src_files:
            file_path = os.path.join(self.src_folder, src_file)
            logger.info(f"Found {src_file}...")
            with open(file_path, "r") as file:
                content = file.read()
                self.context["src"][src_file] = content

        # Render (or copy) each file to the build directory
        logger.info("Rendering files into memory for includes ...")
        for src_file in src_files:
            if not self.context["src"][src_file].startswith("!norender"):
                rendered_content = self.render_template(src_file, lib_content)
                self.context["src"][src_file] = rendered_content

        logger.info("Rendering files onto disk...")
        for src_file in src_files:
            if self.context["src"][src_file].startswith("!norender"):
                rendered_content = self.context["src"][src_file]
            else:
                logger.info(f"Rendering {src_file}")
                rendered_content = self.render_template(src_file, lib_content)

            sections, pure_html = self.parse_special_tags(rendered_content)

            if len(sections):
                logger.info(f"Processing {len(sections)} found in {src_file}")
                self.process_sections(sections)

            if not pure_html.strip():
                logger.warning(f"Not rendering {src_file} as its final content is empty")
                continue

            # Construct full path for build file
            build_file_path = os.path.join(self.build_folder, src_file)
            os.makedirs(os.path.dirname(build_file_path), exist_ok=True)
            with open(build_file_path, "w") as build_file:
                build_file.write(pure_html)
                logger.info(f"Wrote {build_file.name}")

        logger.info("Copying media files ...")
        self.copy_files(self.media_folder, os.path.join(self.build_folder, self.media_folder))
        logger.info("All done")

    def process_sections(self, sections):
        for section in sections:
            section_type = section["opening_tag"]["type"]
            if section_type == "start_page":
                page_name = section["opening_tag"]["page_name"] + ".html"
                build_file_path = os.path.join(self.build_folder, page_name)
                os.makedirs(os.path.dirname(build_file_path), exist_ok=True)
                with open(build_file_path, "w") as build_file:
                    build_file.write(section["_content"])
                    logger.info(f"Wrote {build_file.name} from section")

    def parse_special_tags(self, html_str):
        tag_pattern = re.compile(r"\[---\s*(\S+?)\s*--\s*(\{.*\})\s*\]")
        sections, cleaned_html, stack, content_stack = [], [], [], []

        for line in html_str.splitlines():
            tag_match = tag_pattern.search(line)
            if tag_match:
                json_data = json.loads(tag_match.group(2))
                if stack:
                    last_section = stack.pop()
                    section = {
                        **last_section,
                        "closing_tag": json_data,
                        "_content": "\n".join(content_stack.pop()).strip(),
                    }
                    sections.append(section)
                else:
                    stack.append({"opening_tag": json_data})
                    content_stack.append([])
            elif stack:
                content_stack[-1].append(line)
            else:
                cleaned_html.append(line)

        if stack:
            logger.critical(f"Found unclosed section: \n{content_stack[-1]}")
            raise Exception("Found unclosed section.")

        return sections, "\n".join(cleaned_html)


if __name__ == "__main__":
    jinjapocalypse_instance = Jinjapocalypse()
    jinjapocalypse_instance.process_files()
