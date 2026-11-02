"""
Data Processing Module
Contains documented intentional flaws:
1. Mutable default argument (PY-AST-001)
2. Dangerous eval() execution (PY-AST-004)
3. Division by literal zero (PY-AST-011)
4. Weak MD5 hashing (PY-AST-008)
"""
import hashlib


# Intentional Flaw 1: Mutable default argument
def accumulate_records(entry, cache=[]):
    cache.append(entry)
    return cache


# Intentional Flaw 2: Dangerous dynamic code execution
def evaluate_custom_formula(user_input: str):
    return eval(user_input)


# Intentional Flaw 3: Division by literal zero
def calculate_ratio(total: float):
    return total / 0


# Intentional Flaw 4: Weak MD5 hashing for identifiers
def hash_identifier(data: str):
    return hashlib.md5(data.encode()).hexdigest()
