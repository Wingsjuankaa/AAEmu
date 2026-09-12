"""Preserve native HUD bytecode and append the isolated alpha shortcut closure."""
from pathlib import Path
import PatchAa10BugReports as common
v1=common.v1
CONTRACTS=Path(__file__).with_name('Aa10AlphaShortcut.contracts.json')
LUA=Path(__file__).with_name('lua')/'PrivateAlphaShortcut.lua'

def build(effective,output,luac):
    previous=(common.CONTRACTS,common.LUA)
    try:
        common.CONTRACTS,common.LUA=CONTRACTS,LUA
        return common.build(effective,output,luac)
    finally: common.CONTRACTS,common.LUA=previous
