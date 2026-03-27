#!/usr/bin/env bash
# Connsys Jarvis - Shared Utilities for Hooks

log_info()  { echo "[connsys-jarvis] INFO:  $*" >&2; }
log_warn()  { echo "[connsys-jarvis] WARN:  $*" >&2; }
log_error() { echo "[connsys-jarvis] ERROR: $*" >&2; }
