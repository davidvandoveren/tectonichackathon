"""Which of Kate's two voices a customer hears.

The default follows the gender **registered on the customer record** (a bank knows this from the
ID document / salutation), never a guess from the name. The customer can always switch, and that
choice wins. Unknown or not registered: Kate's default voice.
"""

import threading
from typing import Literal

VoiceKind = Literal["female", "male"]
DEFAULT_VOICE: VoiceKind = "female"

# Stand-in for the customer record's registered gender in this synthetic demo. In production this
# comes from the core banking customer record, not from this table.
REGISTERED_GENDER: dict[str, VoiceKind] = {
    "u_emma": "female",
    "u_marie": "female",
    "u_jan": "male",
    "u_sofie": "female",
}


def default_voice(user_id: str) -> VoiceKind:
    return REGISTERED_GENDER.get(user_id, DEFAULT_VOICE)


class VoicePreferences:
    """The customer's own choice, per customer, in memory."""

    def __init__(self) -> None:
        self._choice: dict[str, VoiceKind] = {}
        self._lock = threading.Lock()

    def voice_for(self, user_id: str) -> VoiceKind:
        with self._lock:
            return self._choice.get(user_id, default_voice(user_id))

    def choose(self, user_id: str, voice: VoiceKind) -> None:
        with self._lock:
            self._choice[user_id] = voice
