"""
NewsReader - 新闻阅读器
自动获取多源新闻，定时刷新，支持分类切换
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
import webbrowser
from datetime import datetime

# ========== 新闻源配置 ==========
NEWS_SOURCES = {
    "Hacker News": {
        "url": "https://hacker-news.firebaseio.com/v0/topstories.json",
        "detail_url": "https://hacker-news.firebaseio.com/v0/item/{}.json",
        "parse": "hackernews",
    },
    "Reddit 科技": {
        "url": "https://www.reddit.com/r/technology/hot.json?limit=20",
        "detail_url": None,
        "parse": "reddit",
    },
    "GitHub Trending": {
        "url": "https://api.github.com/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=20",
        "detail_url": None,
        "parse": "github",
    },
    "Product Hunt": {
        "url": "https://api.github.com/search/repositories?q=created:>2026-06-01&sort=stars&order=desc&per_page=20",
        "detail_url": None,
        "parse": "github_recent",
    },
}

# ========== 颜色主题 ==========
COLORS = {
    "bg": "#1e1e2e",
    "sidebar": "#181825",
    "card": "#313244",
    "accent": "#89b4fa",
    "text": "#cdd6f4",
    "dim": "#6c7086",
    "highlight": "#a6e3a1",
    "warning": "#f9e2af",
    "error": "#f38ba8",
}

REFRESH_INTERVALS = {
    "30 秒": 30,
    "1 分钟": 60,
    "5 分钟": 300,
    "15 分钟": 900,
    "关闭": 0,
}


class NewsReaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📰 NewsReader - 新闻阅读器")
        self.root.geometry("1100x700")
        self.root.minsize(900, 500)
        self.root.configure(bg=COLORS["bg"])

        self.current_source = "Hacker News"
        self.news_data = {}
        self.refresh_seconds = 60
        self.last_refresh = {}
        self.loading = False
        self.auto_refresh_id = None

        self._build_ui()
        self._fetch_all()
        self._start_auto_refresh()

    # ========== UI 构建 ==========
    def _build_ui(self):
        # --- 侧边栏 ---
        sidebar = tk.Frame(self.root, bg=COLORS["sidebar"], width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # Logo
        tk.Label(
            sidebar, text="📰 NewsReader", font=("Segoe UI", 16, "bold"),
            bg=COLORS["sidebar"], fg=COLORS["accent"],
        ).pack(pady=(20, 5))

        tk.Label(
            sidebar, text="实时新闻 · 自动刷新", font=("Segoe UI", 9),
            bg=COLORS["sidebar"], fg=COLORS["dim"],
        ).pack(pady=(0, 20))

        # 新闻源按钮
        tk.Label(
            sidebar, text="新闻源", font=("Segoe UI", 10, "bold"),
            bg=COLORS["sidebar"], fg=COLORS["text"],
        ).pack(anchor=tk.W, padx=15, pady=(10, 5))

        self.source_buttons = {}
        for name in NEWS_SOURCES:
            btn = tk.Button(
                sidebar, text=name, font=("Segoe UI", 10),
                bg=COLORS["card"] if name == self.current_source else COLORS["sidebar"],
                fg=COLORS["accent"] if name == self.current_source else COLORS["text"],
                activebackground=COLORS["card"], activeforeground=COLORS["accent"],
                relief=tk.FLAT, anchor=tk.W, padx=15, pady=8, cursor="hand2",
                command=lambda n=name: self._switch_source(n),
            )
            btn.pack(fill=tk.X, padx=10, pady=2)
            self.source_buttons[name] = btn

        # 刷新间隔
        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=15, pady=15)

        tk.Label(
            sidebar, text="自动刷新", font=("Segoe UI", 10, "bold"),
            bg=COLORS["sidebar"], fg=COLORS["text"],
        ).pack(anchor=tk.W, padx=15, pady=(0, 5))

        self.interval_var = tk.StringVar(value="1 分钟")
        for label in REFRESH_INTERVALS:
            rb = tk.Radiobutton(
                sidebar, text=label, variable=self.interval_var, value=label,
                font=("Segoe UI", 9), bg=COLORS["sidebar"], fg=COLORS["text"],
                selectcolor=COLORS["card"], activebackground=COLORS["sidebar"],
                activeforeground=COLORS["accent"],
                command=lambda: self._change_interval(),
            )
            rb.pack(anchor=tk.W, padx=20)

        # 底部信息
        tk.Label(
            sidebar, text="v1.0 · Made with ❤️", font=("Segoe UI", 8),
            bg=COLORS["sidebar"], fg=COLORS["dim"],
        ).pack(side=tk.BOTTOM, pady=10)

        # --- 主内容区 ---
        main = tk.Frame(self.root, bg=COLORS["bg"])
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 顶栏
        topbar = tk.Frame(main, bg=COLORS["bg"], height=50)
        topbar.pack(fill=tk.X, padx=20, pady=(15, 0))
        topbar.pack_propagate(False)

        self.title_label = tk.Label(
            topbar, text=self.current_source, font=("Segoe UI", 18, "bold"),
            bg=COLORS["bg"], fg=COLORS["text"],
        )
        self.title_label.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            topbar, text="", font=("Segoe UI", 9),
            bg=COLORS["bg"], fg=COLORS["dim"],
        )
        self.status_label.pack(side=tk.LEFT, padx=15)

        self.refresh_btn = tk.Button(
            topbar, text="🔄 刷新", font=("Segoe UI", 10),
            bg=COLORS["card"], fg=COLORS["text"],
            activebackground=COLORS["accent"], activeforeground=COLORS["bg"],
            relief=tk.FLAT, padx=15, pady=5, cursor="hand2",
            command=self._manual_refresh,
        )
        self.refresh_btn.pack(side=tk.RIGHT)

        # 新闻列表（可滚动）
        container = tk.Frame(main, bg=COLORS["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self.news_frame = tk.Frame(canvas, bg=COLORS["bg"])

        self.news_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.news_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.canvas = canvas

    # ========== 数据获取 ==========
    def _fetch_source(self, source_name):
        """在子线程中获取某个新闻源的数据"""
        config = NEWS_SOURCES[source_name]
        items = []
        try:
            headers = {"User-Agent": "NewsReader/1.0"}
            resp = requests.get(config["url"], headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if config["parse"] == "hackernews":
                ids = data[:25]
                for item_id in ids:
                    r = requests.get(
                        config["detail_url"].format(item_id), headers=headers, timeout=10
                    )
                    if r.status_code == 200:
                        item = r.json()
                        if item and item.get("type") == "story":
                            items.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", f"https://news.ycombinator.com/item?id={item_id}"),
                                "meta": f"⭐ {item.get('score', 0)} · 💬 {item.get('descendants', 0)} · by {item.get('by', 'unknown')}",
                                "time": datetime.fromtimestamp(item.get("time", 0)).strftime("%H:%M"),
                            })

            elif config["parse"] == "reddit":
                posts = data.get("data", {}).get("children", [])
                for p in posts[:25]:
                    d = p["data"]
                    items.append({
                        "title": d.get("title", ""),
                        "url": f"https://reddit.com{d.get('permalink', '')}",
                        "meta": f"⬆️ {d.get('score', 0)} · 💬 {d.get('num_comments', 0)} · r/{d.get('subreddit', '')}",
                        "time": datetime.fromtimestamp(d.get("created_utc", 0)).strftime("%H:%M"),
                    })

            elif config["parse"] in ("github", "github_recent"):
                repos = data.get("items", [])
                for r in repos[:25]:
                    items.append({
                        "title": f"{r.get('full_name', '')} — {r.get('description', '')[:80]}",
                        "url": r.get("html_url", ""),
                        "meta": f"⭐ {r.get('stargazers_count', 0)} · 🍴 {r.get('forks_count', 0)} · {r.get('language', 'N/A')}",
                        "time": r.get("updated_at", "")[11:16] if r.get("updated_at") else "",
                    })

        except Exception as e:
            items.append({
                "title": f"❌ 获取失败: {e}",
                "url": "",
                "meta": "请检查网络连接后重试",
                "time": "",
            })

        self.news_data[source_name] = items
        self.last_refresh[source_name] = datetime.now().strftime("%H:%M:%S")

        # 回到主线程更新 UI
        self.root.after(0, lambda: self._render_news(source_name))

    def _fetch_all(self):
        """获取所有新闻源"""
        for name in NEWS_SOURCES:
            self._fetch_source(name)

    def _render_news(self, source_name):
        """渲染指定源的新闻列表"""
        if source_name != self.current_source:
            return

        # 清空
        for w in self.news_frame.winfo_children():
            w.destroy()

        items = self.news_data.get(source_name, [])
        if not items:
            tk.Label(
                self.news_frame, text="暂无新闻数据", font=("Segoe UI", 12),
                bg=COLORS["bg"], fg=COLORS["dim"],
            ).pack(pady=50)
            return

        self.status_label.config(
            text=f"✅ {len(items)} 条 · 更新于 {self.last_refresh.get(source_name, '--')}"
        )

        for i, item in enumerate(items):
            self._create_card(i, item)

    def _create_card(self, index, item):
        """创建单个新闻卡片"""
        card = tk.Frame(
            self.news_frame, bg=COLORS["card"], padx=15, pady=10,
            highlightbackground=COLORS["card"], highlightthickness=1,
        )
        card.pack(fill=tk.X, pady=3, padx=5)

        # 鼠标悬停效果
        def on_enter(e):
            card.configure(highlightbackground=COLORS["accent"], highlightthickness=1)
        def on_leave(e):
            card.configure(highlightbackground=COLORS["card"], highlightthickness=1)
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        # 序号
        tk.Label(
            card, text=f"{index + 1:02d}", font=("Consolas", 14, "bold"),
            bg=COLORS["card"], fg=COLORS["accent"], width=3,
        ).pack(side=tk.LEFT, padx=(0, 10))

        # 内容区
        content = tk.Frame(card, bg=COLORS["card"])
        content.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title_text = item.get("title", "无标题")
        title_lbl = tk.Label(
            content, text=title_text, font=("Segoe UI", 11),
            bg=COLORS["card"], fg=COLORS["text"], wraplength=700,
            justify=tk.LEFT, anchor=tk.W, cursor="hand2",
        )
        title_lbl.pack(anchor=tk.W)

        url = item.get("url", "")
        if url:
            title_lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

        meta_frame = tk.Frame(content, bg=COLORS["card"])
        meta_frame.pack(anchor=tk.W, pady=(5, 0))

        meta_text = item.get("meta", "")
        if meta_text:
            tk.Label(
                meta_frame, text=meta_text, font=("Segoe UI", 9),
                bg=COLORS["card"], fg=COLORS["dim"],
            ).pack(side=tk.LEFT)

        time_text = item.get("time", "")
        if time_text:
            tk.Label(
                meta_frame, text=f"  🕐 {time_text}", font=("Segoe UI", 9),
                bg=COLORS["card"], fg=COLORS["dim"],
            ).pack(side=tk.LEFT, padx=(10, 0))

    # ========== 交互逻辑 ==========
    def _switch_source(self, name):
        self.current_source = name
        self.title_label.config(text=name)
        # 更新按钮样式
        for n, btn in self.source_buttons.items():
            if n == name:
                btn.configure(bg=COLORS["card"], fg=COLORS["accent"])
            else:
                btn.configure(bg=COLORS["sidebar"], fg=COLORS["text"])
        # 刷新或加载已有数据
        if name in self.news_data:
            self._render_news(name)
        else:
            self._fetch_source(name)

    def _manual_refresh(self):
        if self.loading:
            return
        self.refresh_btn.config(text="⏳ 加载中...", state=tk.DISABLED)
        self.status_label.config(text="正在刷新...")

        def do_refresh():
            self._fetch_source(self.current_source)
            self.root.after(0, lambda: self.refresh_btn.config(text="🔄 刷新", state=tk.NORMAL))

        threading.Thread(target=do_refresh, daemon=True).start()

    def _change_interval(self):
        self.refresh_seconds = REFRESH_INTERVALS[self.interval_var.get()]
        self._start_auto_refresh()

    def _start_auto_refresh(self):
        if self.auto_refresh_id:
            self.root.after_cancel(self.auto_refresh_id)
            self.auto_refresh_id = None

        if self.refresh_seconds <= 0:
            return

        def tick():
            if self.refresh_seconds > 0 and not self.loading:
                self._fetch_source(self.current_source)
            self.auto_refresh_id = self.root.after(
                self.refresh_seconds * 1000, tick
            )

        self.auto_refresh_id = self.root.after(self.refresh_seconds * 1000, tick)


def main():
    root = tk.Tk()
    # 尝试设置 DPI 感知
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = NewsReaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
