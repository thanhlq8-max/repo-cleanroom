"""Read-only Docker inventory (v0.6.x).

Docker is queried exclusively through a fixed whitelist of read-only CLI
subcommands. No Docker object is ever created, started, stopped, or removed.
"""
