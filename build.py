#!/usr/bin/env python3
import subprocess
import sys
import os
import shutil

def build_binary():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--name', 'http-test-server',
        '--clean',
        'server.py'
    ]
    
    print("Building binary with PyInstaller...")
    subprocess.run(cmd, check=True)
    
    dist_dir = os.path.join(script_dir, 'dist')
    if os.path.exists(dist_dir):
        for f in os.listdir(dist_dir):
            print(f"Created: {os.path.join(dist_dir, f)}")

if __name__ == '__main__':
    build_binary()