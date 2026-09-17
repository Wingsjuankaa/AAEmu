"""Build the portable local-Documents patch; contains scripts and manifest, no game binary."""
import hashlib
from pathlib import Path
import shutil
import zipfile

REPO = Path(__file__).resolve().parents[1]
OUTPUT = Path('E:/AAEmu/rama_10/artifacts/client-distribution/local-profile-20260916')
PACKAGE = OUTPUT/'AA10-Perfil-local-20260916-r2'

def main():
    PACKAGE.mkdir(parents=True, exist_ok=True)
    for name in ['Perfil-local.ps1','Activar perfil local.cmd','Restaurar perfil original.cmd']:
        shutil.copyfile(REPO/'Scripts/ClientDistribution'/name,PACKAGE/name)
    baseline = REPO/'Scripts/data/aa10-nuia-lan-20260915.manifest.json'
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == 'eec86fae1be0629372d7fb235a7a16290b507b1ea6cb4dc6f6bfa3f90371c56b'
    shutil.copyfile(baseline, PACKAGE/'MANIFEST-SHA256.original.json')
    (PACKAGE/'LEEME-PERFIL-LOCAL.txt').write_text(
        'AA10: perfil local independiente de OneDrive (instalador r2)\n\n'
        'Corrige GetFullPath al iniciar desde el CMD en Windows PowerShell 5.1.\n'
        'Si tienes el paquete anterior, reemplaza sus archivos con estos.\n\n'
        '1. Cierra ArcheAge.\n'
        '2. Extrae TODOS estos archivos en la carpeta del cliente, junto a Jugar en LAN.cmd.\n'
        '   Ejemplo: D:\\AA10-Nuia-Alpha-es_ES-LAN-20260915\\\n'
        '3. Ejecuta Activar perfil local.cmd y espera el mensaje OK.\n'
        '4. Abre el launcher habitual.\n\n'
        'El perfil pasa a Documentos LOCAL\\ArcheAge, normalmente\n'
        'C:\\Users\\tu_usuario\\Documents\\ArcheAge. El instalador muestra la ruta exacta.\n'
        'Crea system.cfg con locale = en_us solo si no existe un perfil local.\n'
        'No descarga ni migra los archivos del perfil de OneDrive.\n'
        'Los ajustes graficos y controles del perfil anterior quedan alli conservados.\n'
        'El juego genera sus otros archivos al arrancar y al guardar.\n\n'
        'Se modifica exclusivamente Bin64\\xlcommon.dll y se actualiza o recupera\n'
        'MANIFEST-SHA256.json. Se exige la version r575 exacta y se guarda respaldo.\n'
        'Ejecuta Verificar cliente.cmd para comprobar el resto de tu copia.\n'
        'Para revertir: cierra el juego y ejecuta Restaurar perfil original.cmd.\n'
        'La reversion conserva ambos perfiles y restaura DLL/manifiesto originales.\n\n'
        'Este parche no confirma ni repara por si solo el fallo de crear personaje.\n',encoding='utf-8')
    archive = OUTPUT/(PACKAGE.name+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(PACKAGE.iterdir()):
            if path.is_file():
                info = zipfile.ZipInfo(path.name, (2026,9,16,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info,path.read_bytes())
    print(archive)
    print('SHA256',hashlib.sha256(archive.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
