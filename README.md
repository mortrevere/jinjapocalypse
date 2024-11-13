# Jinjapocalypse \o/

Jinjapocalypse is a lightweight website builder utilizing Jinja and hourris for template rendering. This tool processes files within specified directories, allowing you to create a static website with ease. This document describes how to build and run Jinjapocalypse using Docker.

## Building the Docker Image

To build the Docker image, open a terminal and navigate to the directory containing your `Dockerfile`. Run the following command:

    docker build -t jinjapocalypse-image .

This command will build the Docker image using the `Dockerfile` provided, naming it `jinjapocalypse-image`.

## Running the Docker Container

To process your files, run the built container. Use the `-v` flag to mount your source directory to the container. Replace `/path/to/your/project` with the absolute path to your project directory:

    docker run --rm -v /path/to/your/project:/jinjapocalypse jinjapocalypse-image

### Options:

- `--rm`: Automatically removes the container when it exits.
- `-v /path/to/your/project:/jinjapocalypse`: Mounts your project directory to the container's `/jinjapocalypse` directory. This allows the container to read from and write files to your host machine.

## Output

- The processed files and static assets will be output to the `build` directory within your mounted folder.

## Troubleshooting

- Ensure your directories (`src`, `media`) and files exist before running the Docker container.
- Check Docker logs by adding `-it` option for interactive mode in case of issues.
