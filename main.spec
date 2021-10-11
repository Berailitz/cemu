# -*- mode: python ; coding: utf-8 -*-
import distutils.sysconfig
from pathlib import Path

block_cipher = None


a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[
                (
                    str(Path(distutils.sysconfig.get_python_lib(), 'capstone', 'lib', 'capstone.dll')),
                    str(Path('lib', 'site-packages'))
                ), (
                    str(Path(distutils.sysconfig.get_python_lib(), 'keystone', 'keystone.dll')),
                    str(Path('lib', 'site-packages', 'keystone'))
                ), (
                    str(Path(distutils.sysconfig.get_python_lib(), 'unicorn', 'lib', 'unicorn.dll')),
                    str(Path('lib', 'site-packages'))
                ), (
                    'cemu',
                    'cemu'
                )],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='main',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
