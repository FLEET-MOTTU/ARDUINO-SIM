#!/usr/bin/env python

'''
setup.py - Python distutils setup file for BreezySLAM package.
Copyright (C) 2014 Simon D. Levy
'''

import sys
import os
from setuptools import setup, Extension
from platform import machine

# --- NOSSA CORREÇÃO PARA O LINKER ---
# Define o caminho para a pasta 'libs' do seu ambiente conda
# e o nome da biblioteca Python para a linkagem.
CONDA_ENV_PATH = os.path.dirname(sys.executable)
PYTHON_LIB_DIR = os.path.join(CONDA_ENV_PATH, 'libs')
# O nome 'python312' corresponde à sua versão do Python 3.12
PYTHON_LIB_NAME = 'python312' 

# --- LÓGICA ORIGINAL DO AUTOR (Preservada) ---
# Support streaming SIMD extensions
OPT_FLAGS = []
SIMD_FLAGS = []
arch = machine()

print(f"Arquitetura detectada: {arch}")

if arch in ['i686', 'x86_64', 'AMD64']: # Adicionado AMD64 para garantir
    SIMD_FLAGS = ['-msse3']
    arch = 'i686'
elif arch == 'armv7l':
    OPT_FLAGS = ['-O3']
    SIMD_FLAGS = ['-mfpu=neon']
else:
    arch = 'sisd'

print(f"Usando otimização para: {arch}")

# Lista de arquivos fonte, montada dinamicamente
SOURCES = [
    'pybreezyslam.c', 
    'pyextension_utils.c', 
    '../c/coreslam.c', 
    '../c/coreslam_' + arch + '.c',
    '../c/random.c',
    '../c/ziggurat.c'
]

# Define a extensão C, agora com os caminhos corretos para o linker
module = Extension(
    'pybreezyslam', 
    sources=SOURCES, 
    extra_compile_args=['-std=gnu99'] + SIMD_FLAGS + OPT_FLAGS,
    
    # --- NOSSA CORREÇÃO PARA O LINKER (Aplicada aqui) ---
    library_dirs=[PYTHON_LIB_DIR],
    libraries=[PYTHON_LIB_NAME]
)

# Metadados do pacote (Preservado)
setup(
    name='BreezySLAM',
    version='0.1',
    description='Simple, efficient SLAM in Python',
    packages=['breezyslam'],
    ext_modules=[module],
    author='Simon D. Levy and Suraj Bajracharya',
    author_email='simon.d.levy@gmail.com',
    url='https://github.com/simondlevy/BreezySLAM',
    license='LGPL',
    platforms='Linux; Windows; OS X',
    long_description='Provides core classes Position, Map, Laser, Scan, and algorithm CoreSLAM'
)