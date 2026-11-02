"""
Application Entry Point
Contains documented intentional flaws:
1. Cross-File Inconsistency: Importing non-existent symbol 'verify_jwt' from auth (CROSS-001)
2. Assert used in business logic (PY-AST-010)
"""
import sys

# Intentional Flaw 1: 'verify_jwt' does not exist in auth.py
from auth import authenticate_user, verify_jwt
from data_processor import accumulate_records


def run_pipeline(user, token):
    # Intentional Flaw 2: Assert used for authorization check
    assert user is not None, "User cannot be None"
    
    if authenticate_user(user, token):
        result = accumulate_records({"user": user, "status": "active"})
        return result
    return None


if __name__ == "__main__":
    print("CodeSentinel sample runner")
