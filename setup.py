from setuptools import setup, find_packages

setup(
    name='licheats',
    version='0.1',
    packages=find_packages(),
    description='Un proyecto para facilitar análisis de partidas en Lichess',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/MrCabss69/licheats',
    # Información adicional
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
