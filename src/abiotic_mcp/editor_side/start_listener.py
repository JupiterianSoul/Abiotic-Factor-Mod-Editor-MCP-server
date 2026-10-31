"""Manual entry point: Tools > Execute Python Script in the Mod Editor."""

import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import abiotic_listener

abiotic_listener.start()
