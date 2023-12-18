import unittest
import os
import tempfile
import io

from mido import MidiFile, MidiTrack, Message

from midi_validator import MidiValidator, MidiValidatorResult
from tests.testcase import TestCase

class MidiValidatorTestCase(TestCase):
    def test_get_error_too_big(self):
        midi_data = b'a' * 1024 * 1024
        self.assertEqual(MidiValidator.get_result(midi_data), MidiValidatorResult.TOO_BIG)

    def test_get_error_fail_parse(self):
        midi_data = b'dummy data'
        self.assertEqual(MidiValidator.get_result(midi_data), MidiValidatorResult.FAIL_PARSE)

    def test_get_error_fail_bad_type(self):
        midi = MidiFile(type=2)
        track = MidiTrack()
        track.append(Message('note_on', note=64, velocity=64, time=0))
        track.append(Message('note_off', note=64, velocity=64, time=32))
        midi.tracks.append(track)
        midi_stream = io.BytesIO()
        midi.save(file=midi_stream)
        self.assertEqual(MidiValidator.get_result(midi_stream.getvalue()), MidiValidatorResult.BAD_TYPE)

    def test_get_error_too_long(self):
        midi = MidiFile(type=1, ticks_per_beat=24)
        track = MidiTrack()
        track.append(Message('note_on', note=64, velocity=64, time=0))
        track.append(Message('note_off', note=64, velocity=64, time=24*2*60*16))
        midi.tracks.append(track)
        midi_stream = io.BytesIO()
        midi.save(file=midi_stream)
        self.assertEqual(MidiValidator.get_result(midi_stream.getvalue()), MidiValidatorResult.TOO_LONG)

    def test_get_error_ok(self):
        midi = MidiFile(type=0)
        track = MidiTrack()
        track.append(Message('note_on', note=64, velocity=64, time=0))
        track.append(Message('note_off', note=64, velocity=64, time=32))
        midi.tracks.append(track)
        midi_stream = io.BytesIO()
        midi.save(file=midi_stream)
        self.assertEqual(MidiValidator.get_result(midi_stream.getvalue()), MidiValidatorResult.OK)
