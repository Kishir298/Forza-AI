"""
A.S.I.S. identity subsystem.
"""

from .identity import Identity, build_identity
from .personality import DEFAULT_PERSONALITY

__all__ = ["Identity", "build_identity", "DEFAULT_PERSONALITY"]
