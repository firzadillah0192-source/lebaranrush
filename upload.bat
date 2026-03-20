@echo off
echo Mengunggah perubahan ke GitHub...
git add .
set /p msg="Masukkan pesan commit (kosongkan untuk default): "
if "%msg%"=="" set msg="Update program via batch script"
git commit -m "%msg%"
git push origin main
echo Selesai! Perubahan sudah ada di GitHub.
pause

