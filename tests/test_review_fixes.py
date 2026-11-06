"""Regression cases reproduced during the backup safety review."""
import json
from pathlib import Path
import tempfile
import unittest

import mido

from test_support import complete_image
from roland_d20_tools import d110, inspect, preservation, rhythm, sound
from roland_d20_tools.core import (
    D20Error, D20Message, MemoryImage, make_messages, require_outputs,
    scan_messages, scan_syx, write_syx,
)


class ReviewFixTests(unittest.TestCase):
    def test_conflicts_and_devices(self):
        msg = make_messages(8, complete_image(4), 16)[0]
        self.assertEqual(len(scan_messages([msg, msg])), 2)
        other = msg.copy(data=(65, 17, *msg.data[2:]))
        with self.assertRaisesRegex(D20Error, "Mixed device"):
            scan_messages([msg, other])
        image = MemoryImage.create(4)
        image.write(0, [1, 2], "fixture")
        with self.assertRaisesRegex(D20Error, "conflicting"):
            image.write(1, [3, 4], "fixture")
        self.assertEqual(image.data, b'\x01\x02\x00\x00')
        conflicting = make_messages(8, complete_image(4), 16)[0]
        payload = list(conflicting.data)
        payload[7], payload[-1] = 1, (payload[-1] - 1) % 128
        with self.assertRaisesRegex(D20Error, "conflicting"):
            scan_messages([msg, msg.copy(data=payload)])

    def test_truncated_recognizable_dt1(self):
        for length in range(4, 9):
            with self.subTest(length=length), self.assertRaisesRegex(D20Error, "malformed"):
                scan_messages([mido.Message('sysex', data=[65, 16, 22, 18] + [0] * (length - 4))])

    def test_all_path_aliases_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, out = root/'in.syx', root/'out.syx'
            source.write_bytes(b'original')
            alias = root/'alias'
            alias.symlink_to(source)
            hardlink = root/'hardlink'
            hardlink.hardlink_to(source)
            for report in (source, alias, hardlink, out):
                with self.subTest(report=report), self.assertRaises(D20Error):
                    d110.convert(source, out, device_id=16, force=True, report_path=report)
            with self.assertRaises(D20Error):
                inspect.write_detailed_report(source, alias, format='json', force=True)
            existing = root/'report'
            existing.write_text('keep')
            with self.assertRaises(D20Error):
                require_outputs(source, [out, existing], False)
            self.assertFalse(out.exists())
            self.assertEqual(source.read_bytes(), b'original')

    def test_unique_coverage_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'partial.syx'
            messages = [make_messages(area, complete_image(1), 16)[0] for area in inspect.COMPLETE_ALL_AREAS]
            messages += [messages[0], make_messages(0x11, complete_image(1), 16)[0]]
            write_syx(source, messages)
            self.assertNotIn('ALL (MIDI DUMP)', inspect.report(source))
            report = json.loads(inspect.detailed_report(source, format='json'))
            rows = report['sections'][0]['rows']
            self.assertTrue(all(row['Bytes present'] == '1' for row in rows))
            self.assertEqual(rows[-1]['Status'], 'Unknown')
            self.assertNotEqual(report['inspection_type'], 'ALL_DUMP')

    def test_tone_ranges_and_explicit_timbre_baseline(self):
        self.assertEqual(len(d110.PARTIAL_MAXIMA), 58)
        valid = bytes(16384)
        d110._validate_tones(valid)
        for offset, value in [(10,13), (12,16), (13,2), (14,97), (14+24,31), (14+57,101), (188+3,2)]:
            invalid = bytearray(valid)
            invalid[offset] = value
            with self.subTest(offset=offset), self.assertRaises(D20Error):
                d110._validate_tones(invalid)
        image = complete_image(1024)
        image.data[:8] = bytes((2, 3, 24, 50, 12, 2, 1, 127))
        converted, count = d110._converted_timbres(image)
        self.assertEqual(converted[:8], bytes((2,3,24,50,12,2,0,0)))
        self.assertEqual(count, 1)
        image.data[6] = 2
        with self.assertRaises(D20Error):
            d110._converted_timbres(image)
        setup = complete_image(340)
        setup.data[3] = 2
        with self.assertRaises(D20Error):
            d110._converted_rhythm(setup, {})

    def test_native_preservation_and_changed_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for module, extension, areas in (
                (sound,'.333', [(5,1024),(7,4864),(8,16384)]),
                (rhythm,'.444', [(9,340),(10,16384),(11,2432),(12,502)]),
            ):
                messages = [D20Message(16,(area,0,0),tuple(bytes(size))) for area,size in areas]
                raw = bytearray(module.encode('ORIGINAL', messages))
                raw[40] = 231  # Opaque header byte has no DT1 equivalent.
                source, export, target = root/('in'+extension), root/('out'+extension+'.syx'), root/('new'+extension)
                source.write_bytes(raw)
                module.convert(source, export, device_id=16, force=False)
                module.convert(export, target, device_id=16, force=False)
                self.assertEqual(target.read_bytes(), raw)
                self.assertTrue(scan_syx(export))
                with self.assertRaises(D20Error):
                    module.convert(source, export, device_id=16, force=False)
                export.write_bytes(export.read_bytes()+b'\n')
                with self.assertRaisesRegex(D20Error, 'export has changed'):
                    module.convert(export, target, device_id=16, force=True)
                self.assertEqual(target.read_bytes(), raw)
                preservation.sidecar(export).write_text('{}')
                with self.assertRaises(D20Error):
                    preservation.restore(export, extension)
                preservation.sidecar(export).unlink()
                result = module.convert(export, target, device_id=16, force=True)
                self.assertIn('Normalized container', result)
                self.assertEqual(target.read_bytes()[40], 0)
