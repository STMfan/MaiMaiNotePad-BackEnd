#!/bin/bash
# Alembic 包装脚本 - 自动使用 configs/alembic.ini

alembic -c configs/alembic.ini "$@"
