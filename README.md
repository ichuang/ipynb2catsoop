# ipynb2catsoop

convert ipython / jupyter notebooks to catsoop page

```
usage: ipynb2catsoop [-h] [-v] [-u UNIT_NAME] [-d DIRECTORY] [--convert-all] [--force] ifn

usage: %prog [args...] notebook.ipynb

positional arguments:
  ifn                   input ipython / jupyter notebook file

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         verbose output
  -u UNIT_NAME, --unit-name UNIT_NAME
                        catsoop unit name (subdir where content.md is to be stored); if unspecified, use current working dir
  -d DIRECTORY, --directory DIRECTORY
                        directory where course content is located
  --convert-all         convert all <inputfn>/*.ipynb notebooks, using <inputfn> as the course content directory
  --force               force conversion even if output is newer than input
```

