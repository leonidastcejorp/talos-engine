"""Talos Engine - Flowcore Automation Framework

A Python automation framework for web automation, form filling,
proxy management, and pipeline monitoring.
"""

from setuptools import setup, find_packages

setup(
    name='flowcore',
    version='1.0.0',
    description='Talos Engine flowcore - Web automation & pipeline framework',
    author='Talos Engine',
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'aiohttp-socks',
        'pyyaml',
        'playwright',
        'python-socks',
        'pillow',
    ],
    entry_points={
        'console_scripts': [
            'flowcore-pipeline=flowcore.scripts.run_pipeline:main',
            'flowcore-proxy-refresh=flowcore.scripts.refresh_proxies:main',
        ],
    },
    python_requires='>=3.9',
)
