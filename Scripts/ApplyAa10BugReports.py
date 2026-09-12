"""V4 personal history: same-size ALB patch, preserving the accepted packed icon."""
import json
import ApplyAa10SpanishUiLayout as tools
import PatchAa10BugReports as patch

def main():
    contract=json.loads(patch.CONTRACTS.read_text(encoding='utf-8'))
    icon=contract['icon']
    tools.SENTINELS += [icon['entry'],'game/scriptsbin64/x2ui/inventory/sort_bag.alb']
    original_build=patch.build
    def build(effective,output,luac):
        patch.v1.require_exact(effective/icon['entry'].removeprefix('game/'),icon['sha256'])
        if (tools.CLIENT/icon['entry']).exists(): raise ValueError('Loose icon would shadow accepted asset')
        return original_build(effective,output,luac)
    patch.build=build
    tools.main(patch_module=patch,backup_prefix='aa10-bug-reports-history')

if __name__=='__main__': main()
