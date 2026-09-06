"""Versioned entry point for the es_ES contextual builder/applicator.
Usage: python Scripts/ApplyAa10ContextualLocalization.py prepare|apply|rollback [patch-id]
prepare is the mandatory dry-run; apply only accepts its immutable revision manifest.
"""
import runpy
import sys
from pathlib import Path
scripts=Path('E:/AAEmu/rama_10/localization/aa10-es-es/scripts')
sys.path.insert(0,str(scripts))
runpy.run_path(str(scripts/'contextual_patch.py'),run_name='__main__')
