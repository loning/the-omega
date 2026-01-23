"""Independent ontic-layer implementation for this paper.

This package is intentionally self-contained and does NOT depend on the paper's
`scripts/` pipeline utilities.
"""

from .ontic_system import EncPair, OnticZeckendorfSystem
from .protocol import ProtocolState, ZeckendorfProtocol
from .observer import Observer, ObserverObservation, Transition
from .view import OnticZeckendorfView

__all__ = [
    "EncPair",
    "OnticZeckendorfSystem",
    "ProtocolState",
    "ZeckendorfProtocol",
    "Transition",
    "Observer",
    "ObserverObservation",
    "OnticZeckendorfView",
]

