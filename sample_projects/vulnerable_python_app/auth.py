"""
Vulnerable Authentication & User Management Module
Contains documented intentional flaws for CodeSentinel testing:
1. Hardcoded Secret Token (PY-AST / Secret Scanner)
2. SQL Injection via string concatenation (PY-AST-009 / Bandit B608)
3. Bare except clause (PY-AST-002)
4. Use of insecure os.system (PY-AST-005)
"""
import os
import sqlite3

# Intentional Flaw 1: Hardcoded secret token
ADMIN_API_KEY = "sk-live-9876543210abcdef9876543210abcdef"


def authenticate_user(username: str, token: str):
    # Intentional Flaw 2: Bare except masking system signals
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        # Intentional Flaw 3: SQL Injection via string concatenation
        query = "SELECT id, role FROM accounts WHERE username = '" + username + "' AND token = '" + token + "'"
        cursor.execute(query)
        user = cursor.fetchone()
        return user
    except:
        return None


def execute_diagnostic_ping(host: str):
    # Intentional Flaw 4: Insecure command execution via os.system
    os.system("ping -c 1 " + host)
