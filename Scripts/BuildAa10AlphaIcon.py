"""Convert the generated alpha HUD icon to the r575-accepted DDS layout."""
import json
from pathlib import Path
from BuildAa10BugReportIcon import convert_icon,digest

def build():
    assets=Path(__file__).parent/'assets/private-alpha'
    manifest=json.loads((assets/'icon.json').read_text())
    source=assets/'alpha-icon-source.png'
    if digest(source)!=manifest['source_sha256']: raise ValueError('Source PNG drift')
    convert_icon(source,assets/'alpha-icon-64.png',assets/'alpha-icon.dds')
    print(digest(assets/'alpha-icon.dds'))

if __name__=='__main__': build()
