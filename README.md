# 📰 NewsReader - 新闻阅读器

一个轻量级桌面新闻阅读器，支持多源聚合和自动刷新。

## ✨ 功能

- 🔥 **多新闻源** — Hacker News、Reddit 科技、GitHub Trending、GitHub 最新热门
- ⏱️ **自动刷新** — 30秒/1分钟/5分钟/15分钟可选，也可关闭
- 🎨 **暗色主题** — 护眼的 Catppuccin 风格 UI
- 🖱️ **一键打开** — 点击标题直接在浏览器中阅读原文
- 📦 **单文件 EXE** — 无需安装 Python，双击即用

## 🚀 使用

直接双击 `dist/newsreader.exe` 运行。

## 🛠️ 从源码构建

```bash
pip install pyinstaller requests
pyinstaller --onefile --windowed --name newsreader newsreader.py
```

## 📋 新闻源

| 来源 | 说明 |
|------|------|
| Hacker News | Y Combinator 科技新闻 Top 25 |
| Reddit 科技 | r/technology 热门帖子 |
| GitHub Trending | GitHub 高星项目 |
| GitHub 最新 | 近期创建的热门新项目 |

## 📄 License

MIT
