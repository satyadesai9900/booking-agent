"""
Agent evaluation suite.

Importing this package points DATA_DIR at a throwaway directory so eval runs never touch real
bookings, users or chat history. It must therefore be imported before anything from `agent`.
"""

import os
import sys
import tempfile

if "agent.storage.booking_db" in sys.modules:
    raise RuntimeError("Import `evals` before `agent` so eval runs use an isolated DATA_DIR.")

os.environ["DATA_DIR"] = os.getenv("EVAL_DATA_DIR") or tempfile.mkdtemp(prefix="booking-evals-")
