#!/usr/bin/env python3
import sys
from src.ac_cdd.cli import app

if __name__ == "__main__":
    # uv run manage.py コマンド で呼び出された際のエントリーポイント
    app()
