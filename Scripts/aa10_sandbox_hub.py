"""Install the curated retail-asset training hub into the isolated, live Zone379 scene."""
from copy import deepcopy
import math
from pathlib import Path

import aa10_sandbox as sandbox
import aa10_sandbox_scenarios as scenes

PRESET = Path(__file__).with_name('aa10_sandbox_training_hub.json')
ROLES = {'specializations': 18870, 'warehouse': 1023, 'weapons': 1497, 'armor': 1498}


def plan(document, preset):
    """Only scene data changes: preserve the isolated account, actor, dummy and authority binding."""
    config = document['MechanicsSandbox']
    scene = scenes.definition(config.get('ZoneKey'))
    expected = {'Enabled': True, 'CharacterName': sandbox.CHARACTER_NAME,
                'CharacterId': sandbox.CHARACTER_ID, 'AccountId': sandbox.ACCOUNT_ID,
                'WorldId': 0, 'InstanceId': 0, 'ZoneKey': scene['zoneKey']}
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError('El perfil no pertenece al sandbox aislado.')
    if preset.get('schema') != 1 or preset.get('CombatProfile') is not True or any(preset.get(key) != expected[key]
                                       for key in ('WorldId', 'InstanceId', 'ZoneKey')):
        raise ValueError('El laboratorio requiere la misma Zone instalada; este control no cambia de mapa.')
    if preset.get('Origin') != scene['origin']:
        raise ValueError('El laboratorio requiere el origen verificado de la sala.')
    services = preset.get('Services', [])
    if len(services) != 4 or {s.get('Role'): s.get('TemplateId') for s in services} != ROLES:
        raise ValueError('El laboratorio requiere los cuatro servicios del catálogo verificado.')
    dummies = preset.get('Dummies', [])
    if len(dummies) != 4 or not isinstance(preset.get('SceneName'), str) or not preset['SceneName'].strip():
        raise ValueError('El laboratorio requiere cuatro objetivos y un nombre.')
    for position in [*dummies, *services]:
        for key, bound in [('Forward', 60), ('Right', 60), ('Up', 10), ('Rotation', 7)]:
            value = position.get(key, 0)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > bound:
                raise ValueError('Una posición del laboratorio queda fuera de los límites admitidos.')
    result = deepcopy(document)
    result['MechanicsSandbox'].update({key: deepcopy(preset[key]) for key in
                                      ('SceneName', 'CombatProfile', 'Origin', 'Dummies', 'Services')})
    return result


def validate(root, configuration=None):
    # Existing registered route also works on a World that loaded its route table before Hot Reload.
    body = {'character': sandbox.CHARACTER_NAME, 'validateOnly': True}
    if configuration is not None:
        body['configuration'] = configuration
    return sandbox.api(root, '/api/mechanics-sandbox/begin', body)


def loaded_profile(root, expected):
    value = validate(root)
    roles = {s['role']: s['templateId'] for s in value.get('services', [])}
    if value.get('sceneName') != expected.get('SceneName', 'Laboratorio AA10') or roles != {
            s['Role']: s['TemplateId'] for s in expected.get('Services', [])}:
        return None
    if not value.get('success') or value.get('state') != 'validated':
        raise ValueError(value.get('message', 'El runtime rechazó el laboratorio antes de modificarlo.'))
    return value


def apply(root):
    root = sandbox.safe_root(root)
    sandbox.verify_runtime_binding(root)
    path = root/'config/Configurations/MechanicsSandbox.json'
    previous = sandbox.read_jsonc(path)
    zone_key = previous['MechanicsSandbox']['ZoneKey']
    preset = PRESET if zone_key == 379 else PRESET.with_name('aa10_sandbox_training_hub_zone411.json')
    candidate = plan(previous, sandbox.read_jsonc(preset))
    # Fail before writing configuration or touching the old scene if this actor cannot be restored.
    preflight = validate(root)
    if not preflight.get('success') or preflight.get('state') != 'validated':
        raise ValueError(preflight.get('message', 'Conecta primero el personaje y espera a que termine el combate.'))
    if not sandbox.zone_ready(sandbox.api(root, '/api/world/zone-manager-status'), zone_key):
        raise ValueError('La Zone activa del sandbox no tiene un heartbeat vigente.')
    runtime_before = sandbox.api(root, '/api/mechanics-sandbox/runtime')
    before = sandbox.command(root, 'status')
    backup = root/'backups'/f'{sandbox.timestamp()}-before-training-hub.json'
    sandbox.write_json(backup, previous)
    scene_touched = False
    try:
        sandbox.write_json(path, candidate)
        published = validate(root, candidate['MechanicsSandbox'])
        if not published.get('success'):
            raise ValueError(published.get('message', 'El runtime rechazó el perfil del laboratorio.'))
        sandbox.wait_for(lambda: loaded_profile(root, candidate['MechanicsSandbox']),
                         'Carga del perfil de laboratorio', seconds=30)
        # Retire the old baseline once, so subsequent resets use the CURRENT ability book.
        sandbox.command(root, 'clear')
        scene_touched = True
        sandbox.wait_for(lambda: sandbox.idle_result(root), 'Retirada del escenario anterior', seconds=30)
        sandbox.command(root, 'begin')
        result = sandbox.wait_for(lambda: sandbox.ready_result(root), 'Creación del laboratorio', seconds=45)
        actors = result.get('services', [])
        if (len(result.get('dummies', [])) != 4 or len(actors) != 4 or
                {s['role']: s['templateId'] for s in actors} != ROLES or
                len({s.get('objectId', 0) for s in actors}) != 4 or any(not s.get('objectId') for s in actors)):
            raise ValueError('El escenario no confirmó los cuatro dummies y los cuatro servicios.')
        runtime_after = sandbox.api(root, '/api/mechanics-sandbox/runtime')
        if runtime_before['pid'] != runtime_after['pid']:
            raise ValueError('World cambió de proceso durante la aplicación del laboratorio.')
        sandbox.capture(root, 'training-hub-applied', {
            'before': before, 'after': result, 'runtimeBefore': runtime_before,
            'runtimeAfter': runtime_after, 'configurationBackup': str(backup)})
        return result
    except Exception as original:
        sandbox.write_json(path, previous)
        try:
            restored = validate(root, previous['MechanicsSandbox'])
            if not restored.get('success'):
                raise ValueError(restored.get('message', 'El runtime rechazó restaurar el perfil anterior.'))
            sandbox.wait_for(lambda: loaded_profile(root, previous['MechanicsSandbox']),
                             'Restauración del perfil anterior', seconds=30)
            if scene_touched:
                sandbox.command(root, 'clear')
                sandbox.wait_for(lambda: sandbox.idle_result(root), 'Retirada del laboratorio parcial', seconds=30)
                sandbox.command(root, 'begin')
                sandbox.wait_for(lambda: sandbox.ready_result(root), 'Restauración del escenario anterior', seconds=45)
        except Exception as recovery:
            raise RuntimeError(f'{original}. Perfil restaurado desde {backup}; recuperación del escenario: {recovery}') from original
        raise
