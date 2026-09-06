"""Deterministic compact builder, using the localization project's reviewed sources.

The output must be a new file. The active client is never edited by this builder.
Use ApplyAa10ContextualLocalization.py prepare/apply for deployment and rollback.
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,'E:/AAEmu/rama_10/localization/aa10-es-es/scripts')
from contextual_patch import selected,build_compact,verify_delta
from build_full_distribution import hash_file

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--expected-sha256',required=True);a=p.parse_args()
    if hash_file(a.input)!=a.expected_sha256.upper():raise SystemExit('Input compact hash mismatch')
    if a.output.exists():raise SystemExit('Output already exists')
    units=selected();print(build_compact(a.input,a.output,units));print(verify_delta(a.input,a.output,units))
