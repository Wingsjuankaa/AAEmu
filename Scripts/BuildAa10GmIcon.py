"""Format conversion of the generated RGBA icon to the proven r575 DDS layout."""
import json
from pathlib import Path
from BuildAa10BugReportIcon import convert_icon, digest

def build():
    assets = Path(__file__).parent/'assets/gm-panel'
    manifest = json.loads((assets/'icon.json').read_text(encoding='utf-8'))
    source = assets/'gm-icon-source.png'
    if digest(source) != manifest['source_sha256']:
        raise ValueError('Source PNG drift')
    convert_icon(source, assets/'gm-icon-64.png', assets/'gm-icon.dds')
    print(digest(assets/'gm-icon.dds'))

if __name__ == '__main__': build()
