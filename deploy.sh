#!/usr/bin/env bash
USER=swadmin
HOST=192.168.11.245
PORT=22
DIR=/var/lib/logstream

rsync -e "ssh -p ${PORT}" -avz --exclude "webui/gradio-env/" --exclude="tmp" --exclude ".git" --exclude "node_modules" --exclude "build" --exclude "output" --exclude "runtime-data/"  . ${USER}@${HOST}:${DIR}
