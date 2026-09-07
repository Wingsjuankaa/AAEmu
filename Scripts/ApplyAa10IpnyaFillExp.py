#!/usr/bin/env python3
"""Dry-run/apply the custom Ipnya UI with the shared verified ALB transaction."""
from ApplyAa10SpanishUiLayout import main
import PatchAa10IpnyaFillExp as patch

if __name__ == '__main__':
    main(patch_module=patch, backup_prefix="aa10-ipnya-fill-exp")
