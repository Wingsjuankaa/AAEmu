import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import Aa10PakAppend as base
import Aa10SandboxZonePak as batch

TESTROOT=batch.ROOT/'artifacts/tests/aa10-zone-pak'
TESTROOT.mkdir(parents=True,exist_ok=True)
WORLD='game/worlds/main_world/world.xml'
ZONE='game/worlds/main_world/level_design/zone/411/zone.xml'
ICON='game/ui/original.bin'
HARNESS=batch.ROOT/'forensics/output/aa10-client-forensics/sandbox-zone-separate-20261029/package/harness/bin/Release/net10.0/PackageHarness.dll'


def fixture(names=None):
    entries=names or [(WORLD,b'old-world'),(ICON,b'native sentinel')]
    payloads,records=bytearray(),[]
    for name,payload in entries:
        offset=len(payloads);padding=base.aligned(len(payload))-len(payload)
        payloads.extend(payload+bytes(padding));r=bytearray(336);raw=name.encode('ascii');r[:len(raw)]=raw
        struct.pack_into('<qqqi',r,264,offset,len(payload),len(payload),padding)
        r[292:308]=hashlib.md5(payload).digest()
        struct.pack_into('<IqqQ',r,308,0x1234,134262620298410395,134262620298410395,0x123456789ABCDEF)
        records.append(base.aes(bytes(r),True))
    extra=bytes(range(256))+bytes(range(80))
    records.append(base.aes(extra,True))
    table=b''.join(records);footer=bytearray(512);footer[:4]=b'WIBO';struct.pack_into('<II',footer,8,len(entries),1)
    return bytes(payloads)+table+bytes(base.aligned(len(table))-len(table))+base.aes(bytes(footer),True)


class SandboxZonePakTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(dir=TESTROOT)
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name);self.pak=self.root/'fixture.pak';self.original=fixture()
        self.pak.write_bytes(self.original)
        self.old_stat=batch._stat(self.pak)

    def contract(self,items=None):
        items=items or [(WORLD,b'new-world with a larger payload',b'old-world'),(ZONE,b'<Zone key="411"/>',None)]
        entries=[]
        for index,(name,payload,old) in enumerate(items):
            path=self.root/f'payload-{index}.bin';path.write_bytes(payload)
            entries.append({'entry':name,'payload_path':str(path),'after_sha256':base.sha(payload),
                            'before_sha256':base.sha(old) if old is not None else None,
                            'before_size':len(old) if old is not None else None})
        return {'schema':1,'patch_id':'fixture-zone411','package':dict(batch._stat(self.pak),sha256=batch.sha_file(self.pak)),
                'entries':entries}

    def test_batch_replacement_growth_addition_preserves_prefix_raw_records_and_tombstones(self):
        m=batch.prepare(self.pak,self.contract(),self.root/'plan')
        self.assertEqual(self.pak.read_bytes(),self.original)
        start,before,count,extras=base.read_tail(io.BytesIO(self.original))
        after=Path(m['suffix_after']['path']).read_bytes()
        final=self.original[:start]+after
        new_start,tail,new_count,new_extras=base.read_tail(io.BytesIO(final))
        self.assertEqual((new_count,new_extras),(count+1,extras))
        self.assertEqual(tail[336:672],before[336:672])
        self.assertEqual(tail[new_count*336:(new_count+extras)*336],before[count*336:(count+extras)*336])
        old_record=base.aes(before[:336]);new_record=base.aes(tail[:336])
        self.assertEqual(old_record[:264],new_record[:264]);self.assertEqual(old_record[308:],new_record[308:])
        self.assertNotEqual(struct.unpack_from('<q',old_record,264),struct.unpack_from('<q',new_record,264))
        self.assertEqual(final[:start],self.original[:start])
        self.assertEqual(m['live_after'],3)

    def test_apply_is_idempotent_by_suffix_bytes_and_rollback_restores_exact_original_and_mtime(self):
        m=batch.prepare(self.pak,self.contract(),self.root/'plan');manifest=self.root/'plan/manifest.json'
        self.assertEqual(batch.apply_plan(manifest)['state'],'applied')
        applied=self.pak.read_bytes();stamp=self.pak.stat().st_mtime_ns
        self.assertEqual(batch.apply_plan(manifest)['state'],'already_patched')
        self.assertEqual(self.pak.read_bytes(),applied);self.assertEqual(self.pak.stat().st_mtime_ns,stamp)
        self.assertEqual(batch.rollback_plan(manifest)['state'],'rolled_back')
        self.assertEqual(self.pak.read_bytes(),self.original)
        self.assertEqual(self.pak.stat().st_mtime_ns,self.old_stat['mtime_ns'])
        self.assertEqual(batch.rollback_plan(manifest)['state'],'already_original')

    @unittest.skipUnless(HARNESS.is_file(),'Requires the separately built forensic C# reader')
    def test_csharp_reader_verifies_new_replaced_and_unrelated_payloads(self):
        self.assertTrue(HARNESS.is_file(),'Build the isolated forensic C# harness; no production build required')
        m=batch.prepare(self.pak,self.contract(),self.root/'plan');batch.apply_plan(self.root/'plan/manifest.json')
        expected={WORLD:base.sha(b'new-world with a larger payload'),ZONE:base.sha(b'<Zone key="411"/>'),ICON:base.sha(b'native sentinel')}
        path=self.root/'expected.json';path.write_text(json.dumps(expected))
        # The standalone checker deliberately bounds writable/read fixture paths to its forensic root.
        # Copy this tiny generated fixture there; no operational package is touched.
        fixture_root=HARNESS.parents[4]/'fixtures';fixture_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_root) as directory:
            check=Path(directory)/'batch.pak';check.write_bytes(self.pak.read_bytes())
            run=subprocess.run(['dotnet',str(HARNESS),'check',str(check),str(path)],capture_output=True,text=True,check=True)
        self.assertTrue(json.loads(run.stdout)['success'])
        self.assertEqual(json.loads(run.stdout)['extras'],1)

    def test_rejects_path_escape_case_collision_duplicate_and_wrong_entry_hash_without_outputs(self):
        for name in ['game/worlds/main_world/../escape','game/worlds/main_world//x',
                     'game/worlds/main_world/X','game/worlds/main_world/x\0evil','game/worlds/main_world/x\\y',
                     'game/scripts/bin/x','game/worlds/other/world.xml']:
            c=self.contract();c['entries'][1]['entry']=name
            with self.subTest(name=name),self.assertRaises((ValueError,UnicodeEncodeError)):
                batch.prepare(self.pak,c,self.root/'bad')
            self.assertFalse((self.root/'bad').exists())
        c=self.contract();c['entries'][1]['entry']=WORLD
        with self.assertRaises(ValueError):batch.prepare(self.pak,c,self.root/'bad')
        c=self.contract();c['entries'][0]['before_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'hash drift'):batch.prepare(self.pak,c,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
        self.assertEqual(self.pak.read_bytes(),self.original)

    def test_add_existing_and_replace_missing_or_unknown_payloads_are_rejected(self):
        for items in [[(WORLD,b'new',None)],[(ZONE,b'new',b'old')]]:
            with self.subTest(items=items),self.assertRaises(ValueError):
                batch.prepare(self.pak,self.contract(items),self.root/'bad')
        self.pak.write_bytes(fixture([('game/worlds/main_world/WORLD.XML',b'old-world'),(ICON,b'native sentinel')]))
        with self.assertRaisesRegex(ValueError,'Case-fold collision'):
            batch.prepare(self.pak,self.contract(),self.root/'bad')

    def test_pinned_source_and_frozen_suffix_drift_are_refused_without_writing(self):
        c=self.contract();c['package']['mtime_ns']-=1
        with self.assertRaisesRegex(ValueError,'identity drift'):batch.prepare(self.pak,c,self.root/'bad')
        m=batch.prepare(self.pak,self.contract(),self.root/'plan')
        Path(m['suffix_after']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Frozen suffix drift'):batch.apply_plan(self.root/'plan/manifest.json')
        self.assertEqual(self.pak.read_bytes(),self.original)

    def test_unchanged_entry_preserves_full_cipher_record_and_deterministic_suffixes(self):
        c=self.contract([(WORLD,b'old-world',b'old-world'),(ZONE,b'new',None)])
        a=batch.prepare(self.pak,c,self.root/'a');b=batch.prepare(self.pak,c,self.root/'b')
        self.assertEqual(a['suffix_after']['sha256'],b['suffix_after']['sha256'])
        before=Path(a['suffix_before']['path']).read_bytes()
        planned=self.original[:a['suffix_offset']]+Path(a['suffix_after']['path']).read_bytes()
        _,after,_,_=base.read_tail(io.BytesIO(planned));self.assertEqual(before[:336],after[:336])
        self.assertEqual(a['entries'][1 if a['entries'][0]['entry']==ZONE else 0]['operation'],'unchanged')

    def test_same_payload_with_requested_filetime_change_is_not_silently_ignored(self):
        c=self.contract([(WORLD,b'old-world',b'old-world')]);c['entries'][0]['modify_filetime']=batch.STAMP
        m=batch.prepare(self.pak,c,self.root/'plan')
        self.assertEqual(m['entries'][0]['operation'],'replace')

    def test_complete_noop_preserves_opaque_fat_padding_without_a_write(self):
        start,tail,count,extras=base.read_tail(io.BytesIO(self.original))
        position=start+(count+extras)*336
        native=bytearray(self.original);native[position:-512]=bytes([0xB5])*(len(native)-512-position)
        self.pak.write_bytes(native);stamp=self.pak.stat().st_mtime_ns
        m=batch.prepare(self.pak,self.contract([(WORLD,b'old-world',b'old-world')]),self.root/'plan')
        self.assertEqual(m['suffix_before']['sha256'],m['suffix_after']['sha256'])
        self.assertEqual(batch.apply_plan(self.root/'plan/manifest.json')['state'],'already_patched')
        self.assertEqual(self.pak.read_bytes(),bytes(native));self.assertEqual(self.pak.stat().st_mtime_ns,stamp)

    def test_runtime_apply_requires_explicit_flag_before_any_writer_call(self):
        with patch.object(batch,'_replace_suffix') as writer:
            with self.assertRaisesRegex(ValueError,'allow_runtime'):
                batch._require_offline(batch.SANDBOX/'client/game_pak',False)
            writer.assert_not_called()

    def test_mid_write_and_post_verify_failures_restore_original_bytes_and_metadata(self):
        original=batch._replace_suffix
        for failure in ('midwrite','postverify'):
            contract=self.contract();m=batch.prepare(self.pak,contract,self.root/f'plan-{failure}')
            calls=[]
            def fail_once(*args,**kwargs):
                calls.append(1)
                if len(calls)==1:
                    target=kwargs['target'];target.seek(m['suffix_offset'])
                    if failure=='midwrite':
                        target.write(b'broken');target.flush();raise OSError('injected write failure')
                    original(*args,**kwargs);target.seek(m['suffix_offset']);target.write(b'broken');target.flush();return
                return original(*args,**kwargs)
            with self.subTest(failure=failure),patch.object(batch,'_replace_suffix',side_effect=fail_once):
                with self.assertRaises((OSError,ValueError)):
                    batch.apply_plan(self.root/f'plan-{failure}/manifest.json')
            self.assertEqual(self.pak.read_bytes(),self.original)
            self.assertEqual(self.pak.stat().st_mtime_ns,contract['package']['mtime_ns'])
            self.assertEqual(len(calls),2)

    @unittest.skipUnless(os.name=='nt','Windows package sharing contract')
    def test_exclusive_writer_prevents_concurrent_package_readers(self):
        with batch._open_exclusive(self.pak):
            with self.assertRaises(OSError):
                with self.pak.open('rb'):pass
        self.assertEqual(self.pak.read_bytes(),self.original)


if __name__=='__main__':unittest.main()
