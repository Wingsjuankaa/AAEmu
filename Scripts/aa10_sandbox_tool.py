"""Desktop controls for the live AA10 development scene; no web hosting or extra dependencies."""
import json
import math
import queue
import threading
import tkinter as tk
from tkinter import ttk
import aa10_sandbox as sandbox
import aa10_sandbox_watch as watch


def layout(count, distance, separation):
    if not 1 <= count <= 16 or not all(math.isfinite(v) for v in (distance, separation)):
        raise ValueError('Selecciona entre 1 y 16 objetivos y distancias finitas.')
    if not 1 <= distance <= 40 or not .5 <= separation <= 8:
        raise ValueError('Distancia: 1–40 m; separación: 0,5–8 m.')
    if count == 1:
        return [{'Forward': distance, 'Right': 0, 'Up': 0}]
    result = [{'Forward': distance, 'Right': 0, 'Up': 0}]
    for index in range(count-1):
        row, column = divmod(index, 3)
        result.append({'Forward': distance+5+row*separation, 'Right': (column-1)*separation, 'Up': 0})
    if any(abs(point['Forward']) > 60 or abs(point['Right']) > 60 for point in result):
        raise ValueError('La combinación supera los 60 m del escenario; reduce objetivos, distancia o separación.')
    return result


def poll_observation(runtime_call, scenario_call):
    """A disconnected character must not discard the new World's valid PID/update state."""
    runtime, scenario = None, None
    try:
        runtime = runtime_call()
    except Exception:
        pass
    try:
        scenario = scenario_call()
    except Exception:
        pass
    return runtime, scenario


class PendingAutoReset:
    """Coalesce code updates until the scenario is ready and the UI worker admits a reset."""
    def __init__(self):
        self.pending = False

    def request(self):
        self.pending = True

    def clear(self):
        self.pending = False

    def try_start(self, enabled, ready, start):
        if not enabled:
            self.clear()
        if self.pending and ready and start():
            self.clear()
            return True
        return False


def start_owned_operation(operation):
    # Closing the controls must not abandon a client hidden during startup:
    # finish the owned operation so Sandbox.start reaches reveal or cancel.
    worker = threading.Thread(target=operation, daemon=False)
    worker.start()
    return worker


def show(runtime_root):
    origin = sandbox.scenes.selected(runtime_root)['origin']
    window = tk.Tk()
    window.title('AA10 · Laboratorio de mecánicas')
    window.geometry('790x610')
    window.minsize(740, 560)
    style = ttk.Style(window)
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    style.configure('TLabel', font=('Segoe UI', 10))
    style.configure('TButton', font=('Segoe UI', 10), padding=7)
    content = ttk.Frame(window, padding=20)
    content.pack(fill='both', expand=True)
    ttk.Label(content, text='Laboratorio de mecánicas · AA10', font=('Segoe UI Semibold', 19)).pack(anchor='w')
    ttk.Label(content, text='Cliente español, personaje Sandbox y modelos originales.').pack(anchor='w', pady=(5, 16))
    state = tk.StringVar(value='Preparando el entorno de desarrollo…')
    reload_state = tk.StringVar(value='Código C#: esperando World')
    scene = tk.StringVar(value='Escenario: esperando conexión')
    ttk.Label(content, textvariable=state, font=('Segoe UI Semibold', 11)).pack(anchor='w')
    ttk.Label(content, textvariable=reload_state).pack(anchor='w', pady=4)
    ttk.Label(content, textvariable=scene, wraplength=740).pack(anchor='w')
    controls = ttk.Frame(content)
    controls.pack(fill='x', pady=16)
    messages = queue.Queue()
    busy = threading.Lock()
    stopped = threading.Event()
    auto_reset = tk.BooleanVar(value=True)
    latest = {'updateCount': None, 'pid': None, 'scenario': None}
    pending_reset = PendingAutoReset()

    def task(label, operation):
        if not busy.acquire(blocking=False):
            return False
        state.set(label)
        def execute():
            try:
                result = operation()
                messages.put(('done', result))
            except Exception as error:
                messages.put(('error', str(error)))
            finally:
                busy.release()
        start_owned_operation(execute)
        return True

    def open_scene():
        def execute():
            watch.prepare(runtime_root)
            sandbox.start(runtime_root, authorize_zone=True)
            return sandbox.command(runtime_root, 'status')
        task('Abriendo el escenario; la ventana aparecerá cuando esté listo…', execute)

    def reset():
        def execute():
            sandbox.command(runtime_root, 'reset')
            result = sandbox.wait_for(lambda: sandbox.ready_result(runtime_root), 'Reset del escenario')
            sandbox.capture(runtime_root, 'tool-reset', result)
            return result
        return task('Restableciendo posiciones, objetivos, buffs y cooldowns…', execute)

    ttk.Button(controls, text='Abrir escenario', command=open_scene).pack(side='left')
    ttk.Button(controls, text='Reiniciar prueba', command=reset).pack(side='left', padx=10)
    def apply_hub():
        from aa10_sandbox_hub import apply
        task('Preparando los cuatro puestos del laboratorio…', lambda: apply(runtime_root))
    ttk.Button(controls, text='Aplicar laboratorio', command=apply_hub).pack(side='left')
    ttk.Checkbutton(content, text='Restablecer la prueba después de una recarga C# compatible',
                    variable=auto_reset).pack(anchor='w', pady=(0, 14))
    editor = ttk.LabelFrame(content, text='Escenario en vivo', padding=12)
    editor.pack(fill='x')
    values = {name: tk.StringVar(value=str(value)) for name, value in
              [('Objetivos', 4), ('Distancia', 5), ('Separación', 2),
               ('X', origin['X']), ('Y', origin['Y']), ('Z', origin['Z'])]}
    for index, (name, value) in enumerate(values.items()):
        row, column = divmod(index, 3)
        ttk.Label(editor, text=name+(' (m)' if name in ('Distancia', 'Separación') else '')).grid(
            row=row*2, column=column, sticky='w', padx=(0, 12), pady=(0, 3))
        ttk.Entry(editor, textvariable=value, width=20).grid(row=row*2+1, column=column,
                                                          sticky='ew', padx=(0, 12), pady=(0, 9))
        editor.columnconfigure(column, weight=1)

    def apply_layout():
        try:
            requested = layout(int(values['Objetivos'].get()), float(values['Distancia'].get()),
                               float(values['Separación'].get()))
            origin = {key: float(values[key].get()) for key in ('X', 'Y', 'Z')}
            if not all(math.isfinite(value) for value in origin.values()):
                raise ValueError('Las coordenadas del escenario deben ser finitas.')
            origin['Rotation'] = 0
        except ValueError as error:
            state.set(str(error))
            return
        def execute():
            result = sandbox.api(runtime_root, '/api/mechanics-sandbox/reconfigure',
                                 {'character': sandbox.CHARACTER_NAME, 'origin': origin, 'dummies': requested})
            if not result.get('success'):
                raise ValueError(result.get('message', 'El escenario no aceptó el cambio.'))
            result = sandbox.wait_for(lambda: sandbox.ready_result(runtime_root), 'Aplicar escenario')
            sandbox.capture(runtime_root, 'tool-layout', result)
            return result
        task('Aplicando el escenario sin reiniciar el cliente…', execute)

    ttk.Button(editor, text='Aplicar posiciones en vivo', command=apply_layout).grid(
        row=4, column=0, columnspan=3, sticky='w', pady=(5, 0))
    ttk.Label(content, text='Los cambios C# compatibles se aplican al código real. Cambios estructurales\n'
              'o del motor nativo pueden requerir reinicio; la herramienta lo indica.',
              foreground='#555555').pack(anchor='w', pady=(15, 8))
    history = tk.Text(content, height=5, wrap='word', font=('Consolas', 9), state='disabled')
    history.pack(fill='both', expand=True)

    def append(text):
        history.configure(state='normal')
        history.insert('end', text+'\n')
        history.see('end')
        history.configure(state='disabled')

    def observe():
        while not stopped.wait(2):
            runtime, scenario = poll_observation(
                lambda: sandbox.api(runtime_root, '/api/mechanics-sandbox/runtime'),
                lambda: sandbox.command(runtime_root, 'status'))
            if runtime is not None or scenario is not None:
                messages.put(('observation', (runtime, scenario)))
            else:
                messages.put(('offline', None))

    def update():
        try:
            while True:
                kind, value = messages.get_nowait()
                if kind == 'done':
                    state.set('Escenario listo para probar.')
                    if isinstance(value, dict):
                        latest['scenario'] = value
                    append('Prueba preparada sin pasos de acceso manuales.')
                elif kind == 'error':
                    state.set('Se requiere atención: '+value)
                    append(value)
                elif kind == 'observation':
                    runtime, scenario = value
                    latest['scenario'] = scenario
                    if scenario is not None:
                        scene.set(f"{scenario.get('sceneName') or 'Escenario'} · intento {scenario.get('attempt', 0)} · "
                                  f"{len(scenario.get('dummies', []))} objetivos · {len(scenario.get('services', []))} servicios · {scenario.get('state', '')}")
                    else:
                        scene.set('Personaje sin conexión; el estado de World se sigue observando.')
                    if runtime is not None:
                        count, pid = runtime.get('updateCount', 0), runtime.get('pid')
                        reload_state.set(('Código C#: recarga en vivo activa' if runtime.get('hotReloadSupported')
                                          else 'Código C#: este proceso requiere compilación/reinicio')+
                                         f' · {count} recargas')
                        if latest['pid'] is not None and pid != latest['pid']:
                            pending_reset.clear()
                            state.set('World se reinició. Pulsa Abrir escenario para recuperar la sesión.')
                            append('El cambio requirió reiniciar World.')
                        elif latest['updateCount'] is not None and count > latest['updateCount']:
                            append('Cambio C# aplicado al proceso en marcha.')
                            if auto_reset.get():
                                pending_reset.request()
                        latest.update(updateCount=count, pid=pid)
                elif kind == 'offline' and not busy.locked():
                    latest['scenario'] = None
                    scene.set('Escenario sin conexión. Abrir escenario recupera el entorno.')
        except queue.Empty:
            pass
        pending_reset.try_start(auto_reset.get(),
                                (latest['scenario'] or {}).get('state') == 'ready', reset)
        if not stopped.is_set():
            window.after(100, update)

    def close():
        stopped.set()
        window.destroy()

    window.protocol('WM_DELETE_WINDOW', close)
    threading.Thread(target=observe, daemon=True).start()
    window.after(100, update)
    window.after(400, open_scene)
    window.mainloop()
