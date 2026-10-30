"""Own loading panel runs in a separate process, with Tcl/Tk on that process's main thread."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SW_SHOWNOACTIVATE = 4
NO_ACTIVATE = 0x0010 | 0x0200

def placement(windows, cover, previous):
    """Cover exactly the renderer, beneath any unrelated windows already above it."""
    _, main, x, y, width, height = max(windows)
    flags = NO_ACTIVATE | (0x0004 if previous == cover else 0)
    return main, (None if previous == cover else previous), x, y, width, height, flags


def place_panel(api, cover, windows, previous, foreground, local_order_only=False):
    """Only move our panel. Never require an external window as a Z-order anchor after denial."""
    main, after, x, y, width, height, flags = placement(windows, cover, previous)
    if local_order_only:
        # HWND_TOP is a constant, not another process's window. Raise our non-activating
        # panel only when the game itself is foreground; otherwise retain its own order.
        after = None
        flags = NO_ACTIVATE | (0 if foreground == main else 0x0004)
    ctypes.set_last_error(0)
    if api.SetWindowPos(cover, after, x, y, width, height, flags):
        return local_order_only
    error = ctypes.get_last_error()
    if error == 5 and not local_order_only:
        return place_panel(api, cover, windows, previous, foreground, True)
    raise ctypes.WinError(error)


def rendering_windows(pid):
    windows = []
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    api.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    api.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    api.GetWindow.restype = wintypes.HWND
    api.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    api.GetAncestor.restype = wintypes.HWND
    api.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    api.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    api.EnumWindows.restype = wintypes.BOOL
    def visit(hwnd, _):
        owner = wintypes.DWORD()
        api.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            rectangle = wintypes.RECT()
            if api.GetWindowRect(hwnd, ctypes.byref(rectangle)):
                width, height = rectangle.right-rectangle.left, rectangle.bottom-rectangle.top
                if width >= 400 and height >= 300:
                    windows.append((width*height, hwnd, rectangle.left, rectangle.top, width, height))
        return True
    callback = callback_type(visit)
    api.EnumWindows(callback, 0)
    return api, windows


class VisibleClient:
    """Normal retail presentation used as the successful diagnostic baseline."""
    def __init__(self, arguments, cwd, env):
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = SW_SHOWNOACTIVATE
        self.process = subprocess.Popen(arguments, cwd=cwd, env=env, startupinfo=startup,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def reveal(self):
        pass

    def cancel(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)



class LoadingClient(VisibleClient):
    def __init__(self, arguments, cwd, env):
        self._closing = False
        temporary = Path(env['TEMP']).resolve()
        if temporary.drive.upper() != 'E:':
            raise ValueError('The loading panel state must stay on E')
        self.directory = Path(tempfile.mkdtemp(prefix='aa10-panel-', dir=temporary))
        self.ready_path = self.directory/'ready.signal'
        self.error_path = self.directory/'error.json'
        interpreter = Path(sys.executable).with_name('pythonw.exe')
        if not interpreter.exists():
            raise RuntimeError('The installed Python needs pythonw.exe for the loading panel')
        super().__init__(arguments, cwd, env)
        args = [str(interpreter), '-B', str(Path(__file__).resolve()), '--game-pid', str(self.process.pid),
                '--ready', str(self.ready_path), '--error', str(self.error_path), '--executable', str(arguments[0])]
        try:
            self.panel = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except BaseException:
            super().cancel()
            raise

    @property
    def _error(self):
        if self.error_path.exists():
            return RuntimeError(json.loads(self.error_path.read_text(encoding='utf-8')).get('error', 'Loading panel failed'))
        code = self.panel.poll()
        if code is not None and not self._closing:
            return RuntimeError(f'Loading panel exited unexpectedly ({code})')
        return None

    def reveal(self):
        self._closing = True
        self.ready_path.write_text('ready', encoding='ascii')
        code = self.panel.wait(timeout=5)
        if self._error or code != 0:
            raise RuntimeError(f'Loading panel failed: {self._error or code}')

    def cancel(self):
        try:
            super().cancel()
        finally:
            self._closing = True
            panel = getattr(self, 'panel', None)
            if panel is not None:
                self.ready_path.write_text('cancelled', encoding='ascii')
                try:
                    panel.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    panel.terminate()

def run_panel(game_pid, ready_path, error_path, executable):
    import tkinter as tk
    from tkinter import ttk
    root = None
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    process = kernel.OpenProcess(0x00100000 | 0x1000, False, game_pid)
    if not process:
        return
    try:
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        name, size = ctypes.create_unicode_buffer(32768), wintypes.DWORD(32768)
        if not kernel.QueryFullProcessImageNameW(process, 0, name, ctypes.byref(size)) or Path(name.value).resolve() != executable.resolve():
            raise RuntimeError('The loading target is not the owned sandbox client')
        root = tk.Tk()
        root.withdraw()
        root.overrideredirect(True)
        root.configure(background='#17212c')
        root.geometry('640x400')
        frame = tk.Frame(root, background='#17212c')
        frame.place(relx=.5, rely=.5, anchor='center')
        tk.Label(frame, text='Preparando laboratorio AA10', foreground='#f1f5f9',
                 background='#17212c', font=('Segoe UI Semibold', 23)).pack(pady=(0, 18))
        tk.Label(frame, text='La arena aparecerá cuando esté lista.\nNo necesitas seleccionar mundo ni personaje.',
                 foreground='#cbd5e1', background='#17212c', font=('Segoe UI', 12)).pack()
        progress = ttk.Progressbar(frame, length=300, mode='indeterminate')
        progress.pack(pady=24)
        progress.start(15)
        root.update_idletasks()
        api, _ = rendering_windows(game_pid)
        cover = api.GetAncestor(root.winfo_id(), 2)
        owner = wintypes.DWORD()
        api.GetWindowThreadProcessId(cover, ctypes.byref(owner))
        if owner.value != os.getpid():
            raise RuntimeError('The loading panel is not owned by this launcher')
        api.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        api.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        api.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        api.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        api.GetForegroundWindow.restype = wintypes.HWND
        # Only our panel: no taskbar entry, no activation, no topmost overlay.
        style = api.GetWindowLongPtrW(cover, -20)
        api.SetWindowLongPtrW(cover, -20, style | 0x08000000 | 0x00000080)
        shown, local_order_only = False, False
        def update():
            nonlocal shown, local_order_only, cover
            try:
                if ready_path.exists() or kernel.WaitForSingleObject(process, 0) != 258:
                    root.destroy()
                    return
                api, windows = rendering_windows(game_pid)
                if windows:
                    main = max(windows)[1]
                    previous = api.GetWindow(main, 3)
                    _, after, x, y, width, height, flags = placement(windows, cover, previous)
                    if not shown:
                        root.deiconify()
                        root.update_idletasks()
                        # Tk can recreate its wrapper after withdrawing/deiconifying.
                        cover = api.GetAncestor(root.winfo_id(), 2)
                        owner = wintypes.DWORD()
                        api.GetWindowThreadProcessId(cover, ctypes.byref(owner))
                        if owner.value != os.getpid():
                            raise RuntimeError('The loading panel wrapper is not owned by this launcher')
                        shown = True
                    # SetWindowPos targets only our own panel, never the game.
                    local_order_only = place_panel(api, cover, windows, previous,
                                                   api.GetForegroundWindow(), local_order_only)
                root.after(30, update)
            except BaseException as error:
                error_path.write_text(json.dumps({'error': str(error), 'operation': 'own-panel-update',
                                                 'winerror': getattr(error, 'winerror', None)}), encoding='utf-8')
                root.destroy()
        root.after(0, update)
        root.mainloop()
    except BaseException as error:
        error_path.write_text(json.dumps({'error': str(error)}), encoding='utf-8')
    finally:
        kernel.CloseHandle(process)
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--game-pid', type=int, required=True)
    parser.add_argument('--ready', type=Path, required=True)
    parser.add_argument('--error', type=Path, required=True)
    parser.add_argument('--executable', type=Path, required=True)
    args = parser.parse_args()
    for path in (args.ready, args.error):
        if path.resolve().drive.upper() != 'E:':
            raise ValueError('Loading state must remain on E')
    run_panel(args.game_pid, args.ready, args.error, args.executable)
