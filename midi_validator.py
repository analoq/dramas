"""Provides validation for MIDI files"""
import io
from enum import Enum

from mido import MidiFile # type: ignore

class MidiValidatorResult(Enum):
    """Possible validation results"""
    OK = "OK"
    TOO_BIG = "MIDI file too big >256 KiB"
    FAIL_PARSE = "MIDI file could not be parsed"
    BAD_TYPE = "MIDI file must be type 0 or type 1"
    TOO_LONG = "MIDI file too long >15 min"

class MidiValidator:
    """Validator for MIDI files"""
    MAX_FILE_SIZE = 256*1024
    MAX_MIDI_LENGTH = 15*60

    @classmethod
    def get_result(cls, midi_data: bytes) -> MidiValidatorResult:
        """Return validation results for given `midi_data`"""
        # check file size
        if len(midi_data) > cls.MAX_FILE_SIZE:
            return MidiValidatorResult.TOO_BIG

        # parse midi
        try:
            midi = MidiFile(file=io.BytesIO(midi_data))
        except OSError:
            return MidiValidatorResult.FAIL_PARSE

        # check type
        if midi.type not in (0, 1):
            return MidiValidatorResult.BAD_TYPE

        # check length
        if midi.length > cls.MAX_MIDI_LENGTH:
            return MidiValidatorResult.TOO_LONG

        return MidiValidatorResult.OK
