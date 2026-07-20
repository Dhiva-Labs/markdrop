import os

# Effectively disable rate limiting for the test suite (must be set before app import)
os.environ.setdefault("MD_RATE_PER_MINUTE", "100000")
os.environ.setdefault("MD_RATE_BURST", "100000")
