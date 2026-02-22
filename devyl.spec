# devyl.spec
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('Logo.png', '.'),
        ('Logo.ico', '.'),
        ('Minecraft.ttf', '.'),
        ('config.py', '.'),
        ('scanner', 'scanner'),
        ('utils', 'utils'),
        ('ui', 'ui'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL.Image',
        'PIL.ImageFilter',
        'PIL.ImageEnhance',
        'pynput',
        'pynput.mouse',
        'pynput._util',
        'pynput._util.win32',
        'requests',
        'tkinter',
        'tkinter.font',
        'json',
        'subprocess',
        'threading',
        'webbrowser',
        'ctypes',
        'ctypes.windll',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Devyl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    onefile=True,
    icon='Logo.ico',
    uac_admin=True,
    upx=False,
    version='version_info.txt',
)
