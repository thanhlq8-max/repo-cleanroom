$ErrorActionPreference = "Stop"

py -m compileall src tests
py -m pytest -q
py -m build
