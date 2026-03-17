@echo off

pip freeze > requirements.txt

pyinstaller -F -n BookDownloader --console main.py
