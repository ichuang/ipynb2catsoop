import glob
from setuptools import setup

def findfiles(pat):
    return [x for x in glob.glob('share/' + pat)]

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='ipynb2catsoop',
    version='0.0.3',
    author='I. Chuang',
    author_email='ichuang@mit.edu',
    packages=['ipynb2catsoop'],
    scripts=[],
    url='https://github.com/ichuang/ipynb2catsoop',
    license='LICENSE',
    description='Converter from and interface between ipython / jupyter notebook and catsoop',
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ipynb2catsoop = ipynb2catsoop.ipynb2catsoop:I2C_CommandLine',
            'catsoop2nb = ipynb2catsoop.catsoop2nb:C2I_CommandLine',
            ],
        },
    install_requires=['nbformat',
                      'IPython',
                      ],
    package_dir={'ipynb2catsoop': 'ipynb2catsoop'},
    test_suite="ipynb2catsoop.test",
)
