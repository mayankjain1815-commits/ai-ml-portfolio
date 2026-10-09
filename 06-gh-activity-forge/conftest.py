"""Ensures the project root is importable when pytest is run directly.

Running ``python -m pytest`` from this directory already puts it on
``sys.path``; this file makes plain ``pytest`` work the same way.
"""
