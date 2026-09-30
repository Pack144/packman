#!/usr/bin/env bash

info()    { echo "  $*"; }
success() { echo "[ok] $*"; }
warn()    { echo "[warn] $*"; }
error()   { echo "[error] $*" >&2; exit 1; }
header()  { echo; echo "======================================"; echo "  $*"; echo "======================================"; }
