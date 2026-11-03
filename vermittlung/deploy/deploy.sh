#!/bin/sh
# Neue Fassung der Vermittlung auf den Server bringen: Code kopieren, Image bauen, Dienst neu starten.
#   vermittlung/deploy/deploy.sh <ssh-host>
# Einmalige Einrichtung siehe vermittlung/README.md, Abschnitt „Betrieb mit nginx und systemd“.
set -eu
HOST=${1:?ssh-Host fehlt}
HERE=$(cd "$(dirname "$0")" && pwd)
TAG=$(git -C "$HERE" rev-parse --short HEAD)
if ! git -C "$HERE" diff --quiet HEAD -- ..; then TAG="$TAG-dirty"; fi
IMAGE="bewerbungsassistent-vermittlung:$TAG"
APP=/opt/bewerbungsassistent-vermittlung

(cd "$HERE/.." && COPYFILE_DISABLE=1 tar -cf - Dockerfile requirements.txt ./*.py deploy/compose.yaml deploy/vermittlung.service) |
  ssh "$HOST" "sudo mkdir -p $APP && sudo tar --warning=no-unknown-keyword -xf - -C $APP"
ssh "$HOST" "cd $APP && sudo docker build -q -t $IMAGE . &&
  echo VERMITTLUNG_IMAGE=$IMAGE | sudo tee /etc/bewerbungsassistent-vermittlung/image.env >/dev/null &&
  if sudo systemctl is-enabled -q bewerbungsassistent-vermittlung; then sudo systemctl restart bewerbungsassistent-vermittlung; fi"
echo "$IMAGE"
