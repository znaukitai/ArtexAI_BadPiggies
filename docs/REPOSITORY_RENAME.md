# Переименование репозитория Artex AI

Владелец: GitHub → репозиторий → Settings → General → Repository name → `Artex-AI` → Rename.

После переименования каждый участник выполняет:

```powershell
git remote set-url origin https://github.com/znaukitai/Artex-AI.git
git remote -v
git fetch origin
git switch artex-update
git pull --ff-only
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Пока владелец не переименовал репозиторий, используйте существующий origin: его URL можно узнать командой `git remote get-url origin`. Ссылки в проекте подготовлены для нового имени, поэтому до переименования они могут не открываться. Эта ветка не слита в main.

GitHub перенаправляет прежние ссылки, но обновите ссылку в заявке на хакатон и презентации. После проверки ветки и согласования с владельцем создайте новый релиз из проверенного коммита: веб-установщик загружает релиз, а не содержимое рабочей ветки.
