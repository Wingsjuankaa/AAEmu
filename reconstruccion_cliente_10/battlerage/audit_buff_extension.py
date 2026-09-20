"""Reanchor the reviewed r575 BuffCreated/Updated consumers; never modifies the PE."""
import argparse
import hashlib
import json
from pathlib import Path
import pefile

EXPECTED = "2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76"
ANCHORS = {
    "updated_reader": 0xABF110, "updated_handler": 0x346460,
    "updated_consumer": 0x6C5C00, "created_handler": 0x34C810,
    "created_consumer": 0x6C93C0, "apply_extend": 0xBD5260,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    args = parser.parse_args()
    raw = args.binary.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED:
        raise SystemExit("Not the immutable r575 release: " + digest)
    pe = pefile.PE(data=raw, fast_load=True)
    assert pe.FILE_HEADER.Machine == 0x8664
    print(json.dumps({"sha256": digest, "architecture": "x86-64", "image_base": hex(pe.OPTIONAL_HEADER.ImageBase),
        "anchors": [{"name": name, "rva": hex(rva), "prefix_64_sha256": hashlib.sha256(pe.get_data(rva, 64)).hexdigest()}
                    for name, rva in ANCHORS.items()]}, indent=2))
