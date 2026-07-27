from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reconstruccion_items_8.item_forensics.ghidra_layouts import (
    parse_ghidra_output,
)


class GhidraLayoutTests(unittest.TestCase):
    def test_recovers_direct_loop_and_instruction_accessors(self) -> None:
        loader = """FORMAT\tAA8_SQL_LOADERS_V1
TASK\texample
SQL\tSELECT id, values1, values2, sound_id FROM example
STRING_MATCHES\t1
FUNCTION_BEGIN\tFUN_example\t39001000
uVar1 = (**(code **)(*p + 0x68))(p,&result,0);
iVar = 0;
do {
  iVar = iVar + 1;
  uVar2 = (**(code **)(*p + 0x68))(p,&result,iVar);
} while (iVar < 2);
(**(code **)(*p + 0x68))(p,&result);
FUNCTION_END
TASK_END
"""
        instructions = """PROGRAM\tx2game.dll
FUNCTION_BEGIN\tFUN_example\t39001000
39001030\tMOV R8D,0x3
39001036\tLEA RDX,[RBP + 0x50]
3900103a\tMOV RCX,RAX
3900103d\tCALL qword ptr [R9 + 0x68]
FUNCTION_END
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            loader_path = root / "loaders.txt"
            instruction_path = root / "instructions.txt"
            loader_path.write_text(loader, encoding="utf-8")
            instruction_path.write_text(instructions, encoding="utf-8")
            result = parse_ghidra_output(loader_path, instruction_path)
        self.assertEqual(1, len(result))
        self.assertEqual("confirmed_static", result[0]["status"])
        self.assertEqual(["68", "68", "68", "68"], result[0]["layout"])

    def test_normalizes_32_bit_accessor_offsets(self) -> None:
        loader = """FORMAT\tAA8_SQL_LOADERS_V1
PROGRAM\tx2game.dll
IMAGE_BASE\t39000000
LANGUAGE\tx86:LE:32:default
TASK\tcrafts
SQL\tSELECT id, orderable, title FROM crafts
STRING_MATCHES\t1
FUNCTION_BEGIN\tFUN_39dc1ff0\t39dc1ff0
uVar9 = (**(code **)(*p + 0x34))(p,&result,0);
bVar5 = (**(code **)(*p + 0x1c))(p,&result,1);
uVar10 = (**(code **)(*p + 0x3c))(p,&result,2);
FUNCTION_END
TASK_END
"""
        with tempfile.TemporaryDirectory() as directory:
            loader_path = Path(directory) / "loaders.txt"
            loader_path.write_text(loader, encoding="utf-8")
            result = parse_ghidra_output(loader_path)
        self.assertEqual(1, len(result))
        self.assertEqual("confirmed_static", result[0]["status"])
        self.assertEqual(["68", "38", "78"], result[0]["layout"])


if __name__ == "__main__":
    unittest.main()
