import math
import os
import struct
import tempfile
import wave
 
import mido

from midi_processor import MidiProcessor
from synth import SynthNull

from tests.testcase import TestCase

class MidiProcessorTestCase(TestCase):
    def test_get_length(self):
        with tempfile.NamedTemporaryFile() as fp:
            midi = mido.MidiFile(ticks_per_beat=24)
            track = mido.MidiTrack()
            track.append(mido.Message('note_on', note=64, velocity=64, time=0))
            track.append(mido.Message('note_off', note=64, velocity=64, time=24*2*60))
            midi.tracks.append(track)
            midi.save(file=fp)
            fp.flush()

            length = MidiProcessor.get_length(fp.name)
            self.assertEqual(length, 60)

    def test_record(self):
         with tempfile.NamedTemporaryFile(suffix='.mid') as fp:
            midi = mido.MidiFile(ticks_per_beat=24)
            track = mido.MidiTrack()
            track.append(mido.Message('note_on', note=64, velocity=64, time=0))
            track.append(mido.Message('note_off', note=64, velocity=64, time=24*2*60))
            midi.tracks.append(track)
            midi.save(file=fp)
            fp.flush()

            wav_path = f'{fp.name}.wav'
            MidiProcessor.record(SynthNull(), fp.name, wav_path)
            self.assertTrue(os.path.exists(wav_path))
            self.assertTrue(os.stat(wav_path).st_size > 0)

    def test_encode(self):
        with tempfile.NamedTemporaryFile() as fp:
            # generate wav file
            wav = wave.open(fp.name, 'wb')
            wav.setnchannels(4)
            wav.setsampwidth(3)
            wav.setframerate(48000)
            for x in range(48000):
                sample = math.sin(2*math.pi*440*x / 48000.) * (2**23-1)
                frame = struct.pack('<i', int(sample))
                wav.writeframes(frame[:-1] + frame[:-1] + frame[:-1] + frame[:-1])
            wav.close()
            
            flac_path = f'{fp.name}.flac'
            MidiProcessor.encode(fp.name, flac_path)

            self.assertTrue(os.path.exists(flac_path))
            self.assertTrue(os.stat(flac_path).st_size > 0)
