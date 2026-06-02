#!/usr/bin/env python3
import sqlite3

print("DB test")

try:
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("DB OK:", cur.fetchone())
    conn.close()
except Exception as e:
    print(f"Error: {e}")
