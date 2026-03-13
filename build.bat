@echo off

if not exist "requirements.txt" (
    pip freeze > requirements.txt
)

pyinstaller -F -n BookDownloader --console main.py
