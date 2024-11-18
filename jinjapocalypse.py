import os
import shutil
import yaml
from jinja2 import Environment, FileSystemLoader
from loguru import logger

class Toolbox():
    @staticmethod
    def hourri():
        return "\\o/"
    def load_yaml(path):
        path = "src/" + path
        with open(path) as f:
            data = yaml.safe_load(f)
            return data


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
        for src_file in src_files:
            if self.context["src"][src_file].startswith("!norender"):
                rendered_content = self.context["src"][src_file]
            else:
                logger.info(f"Rendering {src_file}")
                rendered_content = self.render_template(src_file, lib_content)

            # Construct full path for build file
            build_file_path = os.path.join(self.build_folder, src_file)
            os.makedirs(os.path.dirname(build_file_path), exist_ok=True)
            with open(build_file_path, "w") as build_file:
                build_file.write(rendered_content)
                logger.info(f"Wrote {build_file.name}")

        logger.info("Copying media files ...")
        self.copy_files(
            self.media_folder, os.path.join(self.build_folder, self.media_folder)
        )
        logger.info("All done")


if __name__ == "__main__":
    jinjapocalypse_instance = Jinjapocalypse()
    jinjapocalypse_instance.process_files()
