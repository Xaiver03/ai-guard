# AI Guard

> Mac AI  —  ·  · 

 Claude CodeCodexCursor  AI  Agent  Mac  / Swap /  macOS  App 

[![](https://img.shields.io/github/v/release/Xaiver03/ai-guard?label=&style=flat-square)](https://github.com/Xaiver03/ai-guard/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![](https://img.shields.io/badge/-¥6-orange.svg?style=flat-square)](#)

## 

** DMG**

1.  [Releases ](https://github.com/Xaiver03/ai-guard/releases/latest)
2.  `.dmg` 
3.  DMG Applications 
4. " → "

****

```bash
git clone https://github.com/Xaiver03/ai-guard.git
cd ai-guard
pip install -r requirements.txt
python app_menubar.py
```

## 

- **** — SwapCPU 
- **** —  macOS  warn / crit Swap 
- **** —  Web UIChart.js
- **** —  /  /  SIGKILL
- **** —  PID
- **** —  AI/
- **** —  AI 
- **Claude ** — // token 
- **** — SQLite  50+ ClaudeDeepSeekKimiMiniMaxGLMMiMo 
- **** — rumps  CPUSwap
- **** — SQLite 

## 

|  |  |
|----|------|
|  | Python 3.11+, FastAPI, hypercorn, psutil |
|  |  HTML + Vanilla JS + Chart.js (CDN) |
|  | rumps 0.4.0 |
|  | py2app 0.28 `.app` |
|  | SQLite`~/.aigard/alert_history.db`, `~/.aigard/usage_cache.db` |
|  | `config.toml` |

## 

### 

- macOS 12+
- Python 3.11+ ( pyenv )

### 

```bash
pip install -r requirements.txt
```

### 

```bash
#  http://localhost:8765
python main.py

#  App
python app_menubar.py
```

###  .app

```bash
pip install -r requirements-dev.txt
bash build.sh
open "dist/AI Guard.app"
```

### 

```bash
bash scripts/install_autostart.sh

# 
bash scripts/uninstall_autostart.sh
```

## 

 `config.toml` 

```toml
[alert]
memory_warn = 75       # %
memory_crit = 90
swap_warn = 50
swap_crit = 80
swap_cooldown_sec = 300  # Swap 
disk_warn = 85
disk_crit = 95

[processes]
watch_keywords = ["claude", "codex", "cursor", "python"]

[whitelist]
# 
process_names = []           # 
cmdline_keywords = []        # 

[server]
port = 8765
```

## API 

### 

| Method | Path |  |
|--------|------|------|
| GET | `/api/metrics` |  |
| GET | `/api/stream` | SSE  |
| GET | `/api/processes` | AI  |
| GET | `/api/processes/all` |  |
| GET | `/api/alerts/history` |  20  |
| POST | `/api/processes/{pid}/pause` | SIGSTOP |
| POST | `/api/processes/{pid}/resume` | SIGCONT |
| POST | `/api/processes/{pid}/kill` | SIGTERM |
| POST | `/api/processes/batch/kill-safe` |  |
| POST | `/api/autokill/toggle` |  |

### 

| Method | Path |  |
|--------|------|------|
| GET | `/api/whitelist` |  |
| POST | `/api/whitelist/process-name` |  |
| DELETE | `/api/whitelist/process-name` |  |
| POST | `/api/whitelist/cmdline-keyword` |  |
| DELETE | `/api/whitelist/cmdline-keyword` |  |
| POST | `/api/whitelist/pid` |  PID  |
| DELETE | `/api/whitelist/pid` |  PID |

### Claude 

| Method | Path |  |
|--------|------|------|
| GET | `/api/usage/summary` | // |
| GET | `/api/usage/daily` |  |
| GET | `/api/usage/hourly` |  |
| GET | `/api/usage/monthly` |  |
| GET | `/api/usage/models` |  |
| GET | `/api/usage/projects` |  |
| GET | `/api/usage/sessions` |  |
| POST | `/api/usage/refresh` |  JSONL |

### 

| Method | Path |  |
|--------|------|------|
| GET | `/api/usage/pricing` |  +  |
| POST | `/api/usage/pricing` | SQLite  |
| DELETE | `/api/usage/pricing/{model}` |  |
| POST | `/api/usage/pricing/reset` |  |

## 

```
AI Guard/
 main.py                    # FastAPI  + 
 app_menubar.py             #  App rumps
 config.toml                # 
 setup.py                   # py2app 
 build.sh                   # 
 aigard/
    core/
       monitor.py         # psutil
       alerter.py         # macOS 
       threads.py         # 
       whitelist.py       # 
       usage/             # Claude 
           loader.py      # JSONL 
           calculator.py  # 
           aggregator.py  # //
           pricing.py     # 50+ 
           pricing_repository.py  #  SQLite 
           cache.py       # SQLite 
    api/
       routes.py          #  API 
       whitelist.py       #  API
       bookmarks.py       #  API
       usage.py           # Claude  API
    ui/
       index.html         # 
       usage.html         # Claude 
       bookmarks.html     # 
       css/               # 
       js/                #  JavaScript
    bookmarks/             # 
 assets/                    # App 
 scripts/                   # 
 docs/                      # 
```

## 

 SIGKILL AI 

1. `SIGSTOP` — 
2. 
3. `SIGTERM` — 

 `SIGCONT` 

## 

AI Guard  **100% **MIT 

 **¥6 **

- **/** —  [docs/distribution.md](docs/distribution.md#)
- **** — [https://afdian.net/@your-username](https://afdian.net/@your-username)
- **GitHub Sponsors** — [https://github.com/sponsors/Xaiver03](https://github.com/sponsors/Xaiver03)

Bug 

## 

- [](docs/distribution.md) — 
- [](CLAUDE.md) — 

## License

MIT © 
