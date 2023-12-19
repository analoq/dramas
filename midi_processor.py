"""Handles playing, recording, and encoding of MIDI files"""
import subprocess
import signal
import shutil
import math
import time
import logging
import re

import mido # type: ignore

from synth import Synth

class MidiProcessor:
    """Class for handling processing of MIDI files"""

    @staticmethod
    def get_length(midi_path: str) -> int:
        """Return the length in seconds of the MIDI at `midi_path`"""
        midi_file = mido.MidiFile(midi_path)
        return math.ceil(midi_file.length)

    @staticmethod
    def _reset(synth: Synth):
        """Sends a reset to the MIDI device"""
        port = mido.open_output(synth.get_midi_port())
        message = mido.Message.from_bytes(synth.get_reset_sysex())
        port.send(message)
        port.close()
        time.sleep(1) # give device time to reset

    @staticmethod
    def _get_seq_port_name(synth: Synth) -> str:
        midi_port = synth.get_midi_port()
        seq_ports = [name for name in mido.get_output_names() if name.startswith(midi_port)]
        assert len(seq_ports) == 1
        result = re.match(r'^.*\s(\d+:\d+)$', seq_ports[0])
        assert result is not None
        return result.group(1)

    @staticmethod
    def record(synth: Synth, midi_path: str, wav_path: str):
        """Records given `midi_path` and returns path to WAV file"""
        assert midi_path.endswith('.mid')
        length = MidiProcessor.get_length(midi_path)
        if not shutil.which('arecord'):
            raise RuntimeError("`arecord` command not found")
        if not shutil.which('aplaymidi'):
            raise RuntimeError("`aplaymidi` command not found")
        MidiProcessor._reset(synth)
        record_args = [
            'arecord', '--verbose', '--fatal-errors', '--nonblock',
            '--buffer-size', '96000',
            '--device', synth.get_audio_port(),
            '--rate', '48000',
            '--channels', '4',
            '--format', 'S32_LE',
            '--duration', str(length),
            wav_path
        ]
        logging.info('Running arecord with %s', record_args)
        with subprocess.Popen(record_args,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) as record_proc:
            play_args = ['aplaymidi', '-p', MidiProcessor._get_seq_port_name(synth), midi_path]
            logging.info('Running aplaymidi with %s', play_args)
            with subprocess.Popen(play_args,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE) as play_proc:
                while True:
                    time.sleep(1)
                    play_result = play_proc.poll()
                    record_result = record_proc.poll()
                    if play_result is not None:
                        logging.info('play process exited with "%s"', play_result)
                        play_out, play_err = play_proc.communicate(timeout=60)
                        logging.info(play_out.decode('ascii'))
                        logging.info(play_err.decode('ascii'))
                        if play_proc.returncode:
                            raise RuntimeError("Play process exited with error")
                    if record_result is not None:
                        logging.info('record process exited with "%s"', record_result)
                        record_out, record_err = record_proc.communicate(timeout=60)
                        logging.info(record_out.decode('ascii'))
                        logging.info(record_err.decode('ascii'))
                        if not play_result:
                            logging.info('Exiting play process...')
                            play_proc.send_signal(signal.SIGTERM)
                        if record_proc.returncode:
                            raise RuntimeError("Record process exited with error")
                        break

    @staticmethod
    def encode(wav_path: str, flac_path: str):
        """Encodes given `wav_path` and returns path to FLAC file"""
        logging.info('Starting encoding of "%s"...', wav_path)
        if not shutil.which('sox'):
            raise RuntimeError("`sox` command not found")
        encode_args = [
            'sox',
            wav_path,
            '-b', '24',
            flac_path,
            'remix', '1', '2',
            'norm', '-3',
        ]
        logging.info('Running sox with %s', encode_args)
        with subprocess.Popen(encode_args,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) as encode_proc:
            encode_out, encode_err = encode_proc.communicate(timeout=60)
            logging.info('Encode process exited with "%s"', encode_proc.returncode)
            logging.info(encode_out.decode('ascii'))
            logging.info(encode_err.decode('ascii'))
            if encode_proc.returncode:
                raise RuntimeError("Encode process exited with error")
