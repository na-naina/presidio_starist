#!/bin/zsh
rm -rf presidio-venv
python3.10 -m venv presidio-venv
source presidio-venv/bin/activate
pip install --upgrade pip setuptools
pip install -r requirements.txt