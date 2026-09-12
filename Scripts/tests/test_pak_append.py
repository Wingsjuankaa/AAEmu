import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import Aa10PakAppend as a
import ApplyAa10SpanishUiLayout as tools

NAME='game/ui/custom/aaemu/bug_report.dds'

def fixture(extras=1):
    payload=b'native data';record=bytearray(336)
    name=b'game/ui/original.bin';record[:len(name)]=name
    struct.pack_into('<qqqi',record,264,0,len(payload),len(payload),512-len(payload))
    # The reader must preserve opaque metadata and extra/deleted records.
    record[292:308]=bytes(range(16))
    records=a.aes(bytes(record),True)+a.aes(bytes(336),True)*extras
    footer=bytearray(512);footer[:4]=b'WIBO';struct.pack_into('<II',footer,8,1,extras)
    return payload+bytes(512-len(payload))+records+bytes(a.aligned(len(records))-len(records))+a.aes(bytes(footer),True)

class PakAppendTests(unittest.TestCase):
    def test_preserves_records_payload_and_reopens_with_aapak(self):
        original=fixture();payload=b'custom icon data'
        plan=a.prepare(io.BytesIO(original),NAME,payload)
        result=original[:plan['offset']]+plan['after']
        start,tail,count,extras=a.read_tail(io.BytesIO(result))
        self.assertEqual((count,extras),(2,1))
        self.assertEqual(result[:512],original[:512])
        self.assertEqual(tail[:336],plan['before'][:336])
        self.assertEqual(tail[672:1008],plan['before'][336:672])
        with tempfile.TemporaryDirectory() as d:
            pak=Path(d)/'test.pak';pak.write_bytes(result)
            self.assertEqual(tools.extract(pak,NAME,Path(d)/'icon'),a.sha(payload))
            self.assertEqual(tools.extract(pak,'game/ui/original.bin',Path(d)/'native'),a.sha(b'native data'))
        again=a.prepare(io.BytesIO(result),NAME,payload)
        self.assertTrue(again['already']);self.assertEqual(again['before'],again['after'])

    def test_rejects_collision_bad_layout_and_native_paths(self):
        original=fixture(0);p=a.prepare(io.BytesIO(original),NAME,b'icon')
        result=original[:p['offset']]+p['after']
        with self.assertRaises(ValueError): a.prepare(io.BytesIO(result),NAME,b'other')
        with self.assertRaises(ValueError): a.prepare(io.BytesIO(original),'game/ui/original.bin',b'new')
        with self.assertRaises(ValueError): a.prepare(io.BytesIO(bytes(1024)),NAME,b'icon')
        with self.assertRaises(ValueError): a.prepare(io.BytesIO(original),NAME.replace('aaemu/','aaemu/../'),b'icon')

    def test_exact_rollback_and_drift_rejection(self):
        original=fixture();p=a.prepare(io.BytesIO(original),NAME,b'icon')
        with tempfile.TemporaryDirectory() as d:
            pak=Path(d)/'test.pak';pak.write_bytes(original)
            a.write_suffix(pak,p['offset'],p['before'],p['after'])
            with self.assertRaises(ValueError): a.write_suffix(pak,p['offset'],p['before'],p['after'])
            a.write_suffix(pak,p['offset'],p['after'],p['before'])
            self.assertEqual(pak.read_bytes(),original)

    def test_native_dds_header_alpha_and_mip_chain(self):
        from PIL import Image
        asset=tools.REPO/'Scripts/assets/bug-report/report-icon.dds'
        data=asset.read_bytes();header=struct.unpack('<31I',data[4:128])
        self.assertEqual(header[:7],(124,0xA1007,64,64,16384,0,7))
        self.assertEqual(header[18:27],(32,0x41,0,32,0xff0000,0xff00,0xff,0xff000000,0x401008))
        self.assertEqual(len(data),128+sum(s*s*4 for s in (64,32,16,8,4,2,1)))
        self.assertEqual(Image.open(asset).getextrema()[3],(0,255))

if __name__=='__main__': unittest.main()
