"""Offline scene construction regressions: no packages, runtime or windows are opened."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SPEC = importlib.util.spec_from_file_location('sandbox_zone_assets',Path(__file__).parents[1]/'BuildAa10SandboxZoneAssets.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
TEST_ROOT = builder.ARTIFACTS/'tests/zone-assets'
TEST_ROOT.mkdir(parents=True,exist_ok=True)


def world_xml():
    sectors = ''.join(f'<sector x="{x}" y="{y}"/>' for x in range(16) for y in range(16))
    return (f'<World name="{builder.SOURCE_WORLD}" resolution="1024" unitSize="2" cellXCount="2" '
            'cellYCount="2" isInstance="1" oceanLevel="100" maxTerrainHeight="4096">'
            f'<ZoneList><Zone name="{builder.SOURCE_WORLD}" id="406" originX="0" originY="0">'
            '<cellList><cell x="0" y="0"><sectorList>'+sectors+
            '</sectorList></cell></cellList></Zone></ZoneList></World>').encode()


def leveldata():
    return (b'<LevelData><LevelInfo Name="406" HeightmapSize="4096" HeightmapUnitSize="2" '
            b'HeightmapMaxHeight="4096" WaterLevel="100" TerrainSectorSizeInMeters="64"/>'
            b'<Vegetation><Object Id="0" FileName="objects/grass.cgf"/></Vegetation>'
            b'<Note value="{123-406-ABC}"/></LevelData>')


class SceneAssetBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.root = Path(self.temporary.name)
        self.assertTrue(self.root.resolve().is_relative_to(builder.ARTIFACTS.resolve()))
        self.source = self.root/'source'
        self.source.mkdir()
        self.payloads = {name:b'opaque-'+name.encode() for name in (
            'surface.xml','vegetation.xml','env.xml','cells/000_000/client/terrain/heightmap.dat',
            'cells/000_000/client/terrain/cover.ctc','cells/000_000/client/brush.dat',
            'cells/000_000/client/object.dat','cells/000_000/client/statobjs.dat',
            'zone/instance_training_camp_1on1_ga_user.xml','zone/406/editor/level_editor.xml')}
        self.payloads.update({'world.xml':world_xml(),'world.g':(
            f'name {builder.SOURCE_WORLD}\ncellX 2\ncellY 2\noceanLevel 100\nzones\n'
            f'    zone ( name {builder.SOURCE_WORLD}, id 406 )\ncells\n'
            '    cell ( x 0, y 0, zones 406 )\n    cell ( x 0, y 1 )\n').encode(),
            'cells/000_000/client/leveldata.xml':leveldata(),'zone/406/leveldata.xml':leveldata(),
            'level_design/zone/406/editor/npc.xml':b'<ZoneNPCData><aiPathList/></ZoneNPCData>'})
        self.payloads.update({name:b'authored-placement-'+name.encode() for name in builder.OMITTED})
        for name,data in self.payloads.items():
            path = self.source/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        self.manifest = self.root/'source-manifest.json'
        manifest = {'kind':'read-only-static-donor-analysis','world':{'name':builder.SOURCE_WORLD},
            'manifest':[{'relative':name,'size':len(data),'sha256':builder.sha256(data)}
                        for name,data in sorted(self.payloads.items())]}
        self.manifest.write_bytes(builder.json_bytes(manifest))
        self.manifest_pin = patch.object(builder,'SOURCE_MANIFEST_SHA256',builder.sha256(self.manifest.read_bytes()))
        self.count_pin = patch.object(builder,'SOURCE_FILE_COUNT',len(self.payloads))
        self.manifest_pin.start()
        self.count_pin.start()

    def tearDown(self):
        self.count_pin.stop()
        self.manifest_pin.stop()
        # This is the owned temporary directory validated under E artifacts in setUp.
        self.temporary.cleanup()

    def build(self,name='output'):
        return builder.build(self.source,self.root/name,self.manifest)

    def test_new_world_keeps_native_geometry_and_replaces_both_identity_consumers(self):
        manifest,state = self.build()
        output = self.root/'output'
        self.assertEqual(state,'built')
        world = ET.fromstring((output/(builder.PACKAGE_PREFIX+'world.xml')).read_bytes())
        self.assertEqual(world.get('name'),'main_world')
        self.assertEqual(world.get('isInstance'),'0')
        zones = world.findall('./ZoneList/Zone')
        self.assertEqual(len(zones),1)
        self.assertEqual(zones[0].get('id'),'411')
        self.assertEqual(zones[0].get('name'),'aa10_sandbox_lab')
        self.assertEqual(len(zones[0].findall('.//sector')),256)
        native_g = (output/(builder.PACKAGE_PREFIX+'world.g')).read_text()
        self.assertIn('name main_world',native_g)
        self.assertIn('name aa10_sandbox_lab, id 411',native_g)
        self.assertIn('x 0, y 0, zones 411',native_g)
        self.assertNotIn(builder.SOURCE_WORLD,native_g)
        self.assertNotIn('379',(output/(builder.PACKAGE_PREFIX+'world.xml')).read_text())
        for name in ('cells/000_000/client/terrain/heightmap.dat','cells/000_000/client/terrain/cover.ctc',
                     'cells/000_000/client/brush.dat','cells/000_000/client/object.dat','surface.xml','vegetation.xml'):
            self.assertEqual((output/(builder.PACKAGE_PREFIX+name)).read_bytes(),self.payloads[name])
        self.assertEqual(manifest['destination']['origin'],{'X':575,'Y':506,'Z':260,'Rotation':0})
        self.assertEqual(manifest['sourceFiles'],len(self.payloads))

    def test_levelinfo_rewrites_are_scoped_and_zone_metadata_survives(self):
        self.build()
        output = self.root/'output'
        for name in ('cells/000_000/client/leveldata.xml','zone/411/leveldata.xml'):
            data = (output/(builder.PACKAGE_PREFIX+name)).read_bytes()
            self.assertIn(b'Name="411"',data)
            self.assertIn(b'FileName="objects/grass.cgf"',data)
            self.assertIn(b'{123-406-ABC}',data)  # Do not corrupt GUIDs containing donor digits.
        self.assertTrue((output/(builder.PACKAGE_PREFIX+'zone/aa10_sandbox_lab_user.xml')).is_file())
        self.assertFalse((output/(builder.PACKAGE_PREFIX+'zone/406')).exists())

    def test_only_declared_placements_are_omitted_without_fabricated_spawn_files(self):
        manifest,_ = self.build()
        self.assertEqual({item['source'] for item in manifest['omitted']},set(builder.OMITTED))
        for item in manifest['omitted']:
            self.assertEqual(item['sourceSha256'],builder.sha256(self.payloads[item['source']]))
            self.assertTrue(item['reason'])
        entries = {item['entry'] for item in manifest['files']}
        self.assertFalse(any(name.endswith('npc_spawners.g') for name in entries))
        self.assertIn(builder.PACKAGE_PREFIX+'level_design/zone/411/editor/npc.xml',entries)
        for name,data in self.payloads.items():
            self.assertEqual((self.source/name).read_bytes(),data)

    def test_two_outputs_are_identical_and_rerun_does_not_write(self):
        first,_ = self.build('one')
        second,_ = self.build('two')
        self.assertEqual(builder.json_bytes(first),builder.json_bytes(second))
        marker = self.root/'one'/builder.MANIFEST_NAME
        before = marker.stat().st_mtime_ns
        _,state = self.build('one')
        self.assertEqual(state,'already-built')
        self.assertEqual(marker.stat().st_mtime_ns,before)
        first_files = builder.physical_tree_files(self.root/'one')
        second_files = builder.physical_tree_files(self.root/'two')
        self.assertEqual(set(first_files),set(second_files))
        self.assertTrue(all(first_files[name].read_bytes()==second_files[name].read_bytes() for name in first_files))

    def test_input_hash_or_membership_drift_fails_before_creating_output(self):
        path = self.source/'cells/000_000/client/terrain/heightmap.dat'
        path.write_bytes(b'drift')
        with self.assertRaisesRegex(ValueError,'payload drift'):
            self.build()
        self.assertFalse((self.root/'output').exists())
        path.write_bytes(self.payloads['cells/000_000/client/terrain/heightmap.dat'])
        (self.source/'unlisted.txt').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError,'complete donor file tree'):
            self.build()
        self.assertFalse((self.root/'output').exists())

    def test_modified_or_partial_existing_output_is_never_overwritten(self):
        self.build()
        target = self.root/'output'/(builder.PACKAGE_PREFIX+'cells/000_000/client/brush.dat')
        target.write_bytes(b'keep-modified-output')
        with self.assertRaisesRegex(ValueError,'refusing to overwrite'):
            self.build()
        self.assertEqual(target.read_bytes(),b'keep-modified-output')

    def test_manifest_pin_and_output_scope_reject_runtime_c_drive_and_overlap(self):
        for output in (Path('C:/sandbox-zone'),builder.PROJECT/'runtime/sandbox-aa10',
                       builder.ARTIFACTS,self.source/'child',self.root):
            with self.subTest(output=output),self.assertRaises(ValueError):
                builder.build(self.source,output,self.manifest)
        self.manifest.write_bytes(self.manifest.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'pinned donor evidence'):
            self.build()

    def test_world_shape_scale_and_native_g_identity_are_not_guessed(self):
        for old,new in ((b'unitSize="2"',b'unitSize="4"'),(b'id="406"',b'id="407"'),
                        (b'<sector x="0" y="0"/>',b''),(b'originX="0"',b'originX="1"')):
            with self.subTest(old=old),self.assertRaises(ValueError):
                builder.rewrite_world_xml(world_xml().replace(old,new))
        with self.assertRaises(ValueError):
            builder.rewrite_world_g(self.payloads['world.g'].replace(b'zones 406',b'zones 302'))
        with self.assertRaises(ValueError):
            builder.rewrite_leveldata(leveldata().replace(b'WaterLevel="100"',b'WaterLevel="200"'))


if __name__=='__main__':
    unittest.main()
