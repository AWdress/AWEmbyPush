@echo off
chcp 65001 >nul
echo ====================================
echo 正在推送到 GitHub...
echo ====================================

git add .
git commit -m "docs: update contributors to thanks section"
git push origin main --force

echo.
echo ====================================
echo 推送标签...
echo ====================================
git push origin v4.2.0 --force
git push origin v4.3.0 --force

echo.
echo ====================================
echo 完成！
echo ====================================
pause

