@echo off
cd /d "f:\小说ai"

echo === 1. 设置 GitHub 远程仓库 ===
git remote remove origin 2>nul
git remote add origin https://github.com/zhdsg123/novel.git

echo === 2. 推送代码 ===
git push -u origin main

echo === 3. 完成！ ===
echo 现在打开 https://share.streamlit.io
echo Sign in with GitHub → New app → 选择 zhdsg123/novel / main / app.py
echo 部署后在 Settings → Secrets 添加：LLM_API_KEY
pause
