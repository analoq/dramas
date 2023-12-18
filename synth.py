"""Classes to represent a synthesizer"""
from abc import ABC, abstractmethod

class Synth(ABC):
    """Base class for a synthesizer"""
    @abstractmethod
    def get_reset_sysex(self) -> bytes:
        """Return sysex bytes needed to reset synth to initial state"""

    @abstractmethod
    def get_id(self) -> str:
        """Return identifier for synth"""

    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable name for synth"""

    @abstractmethod
    def get_midi_port(self) -> str:
        """Get the MIDI port the synth is attached to"""

    @abstractmethod
    def get_audio_port(self) -> str:
        """Get the audio port the synth is attached to"""

    @staticmethod
    def from_id(synth_id: str) -> 'Synth':
        """Create a Synth class from a given `synth_id`"""
        if synth_id == 'sc55mk2':
            return SynthRolandSC55mk2()
        raise TypeError(f'Synth "{synth_id}" unavailable')

    def __eq__(self, other) -> bool:
        return self.get_name() == other.get_name()

class SynthNull(Synth):
    """Dummy synthesizer for testing"""
    def get_id(self) -> str:
        return "nullsynth"

    def get_name(self) -> str:
        return "Null Synthesizer"

    def get_midi_port(self) -> str:
        return "Midi Through:Midi Through Port-0"

    def get_audio_port(self) -> str:
        return "null"

    def get_reset_sysex(self) -> bytes:
        return b'\xF0\x41\x10\x42\x12\x40\x00\x7F\x00\x41\xF7'

class SynthRolandSC55mk2(Synth):
    """Roland SC55mk2 Synthesizer class"""
    def get_id(self) -> str:
        return "sc55mk2"

    def get_name(self) -> str:
        return "Roland SC55mk2"

    def get_midi_port(self) -> str:
        return "U-44:U-44 ZOOM U-44 MIDI I/O Port"

    def get_audio_port(self) -> str:
        return "hw:CARD=U44"

    def get_reset_sysex(self) -> bytes:
        return b'\xF0\x41\x10\x42\x12\x40\x00\x7F\x00\x41\xF7'
