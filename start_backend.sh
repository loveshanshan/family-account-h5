#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export DATABASE_URL="sqlite+aiosqlite:///./family_account.db"
python main.py
