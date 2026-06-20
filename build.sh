#!/usr/bin/env sh

set -eu

IMAGE_NAME="${IMAGE_NAME:-jinjapocalypse}"
BASE_IMAGE="${BASE_IMAGE:-python:3.12}"

docker build \
  --build-arg BASE_IMAGE="$BASE_IMAGE" \
  -t "$IMAGE_NAME" \
  .
