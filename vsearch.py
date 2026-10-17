#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全平台热点搜索 / 热榜 / 爬取分析器（Arsenal-VideoSearch / HotSearch Pro）
============================================================
经 CDP 驱动本机 Chrome(9222) 打开各平台搜索页 / 热榜页，抽取视频/图文卡(标题/作者/热度)，
做跨平台热点分析(热门创作者 / 高频词 / 内容角度 / 平台分布)。
覆盖：bilibili 哔哩哔哩 / douyin 抖音 / kuaishou 快手 / weibo 微博 / zhihu 知乎 /
      xiaohongshu 小红书 / baidu 百度热搜 / tiktok(TikTok 网页)。
抖音/快手/TikTok 的重活(无水印下载/全量数据)对接 Evil0ctal/Douyin_TikTok_Download_API（自托管）。

用法：
  python vsearch.py hot                       # 实时热榜聚合(各平台 TOP)
  python vsearch.py search "关键词"            # 关键词跨平台搜索+分析
  python vsearch.py bilibili "关键词" [--n 20] # 单平台搜索
  python vsearch.py douyin "关键词"            # 抖音搜索(可能需登录态)
依赖：本机 Chrome 开 9222 调试端口(见下方 launch_chrome)；websocket 库(pip install websocket-client)。
"""
import json, time, sys, argparse, urllib.request, urllib.parse, urllib.error, websocket
from collections import Counter
import re

CDP_PORT = 9222
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# ---------- 平台配置 ----------
# js 返回 JSON 数组：[{title, author, heat}]
PLATFORMS = {
    "bilibili": {
        "name": "哔哩哔哩",
        "search": "https://search.bilibili.com/all?keyword={}",
        "hot": "https://www.bilibili.com/v/popular/rank/all",
        "js": """(()=>{const o=[];document.querySelectorAll('.bili-video-card').forEach(c=>{
  const t=c.querySelector('.bili-video-card__title, h3 a, .title');
  const u=c.querySelector('.bili-video-card__author, .bili-video-card__info--author');
  let ti=t?(t.getAttribute('title')||t.innerText||'').trim():''; if(!ti){const a=c.querySelector('a[title]');if(a)ti=(a.getAttribute('title')||'').trim();}
  o.push({title:ti, author:u?u.innerText.trim():''});});
  if(!o.length){document.querySelectorAll('a[title]').forEach(a=>{const ti=a.getAttribute('title');if(ti&&ti.length>4)o.push({title:ti.trim(),author:''});});}
  return JSON.stringify(o.slice(0,40));})()""",
    },
    "douyin": {
        "name": "抖音",
        "search": "https://www.douyin.com/search/{}",
        "hot": "https://www.douyin.com/hot",
        "js": """(()=>{const o=[];document.querySelectorAll('li[data-e2e="search-card-video"], .search-card-video, article').forEach(c=>{
  const t=c.querySelector('a[title], .title, [data-e2e="search-card-video-title"]');
  const u=c.querySelector('[data-e2e="search-card-video-author"], .author, .nickname');
  let ti=t?(t.getAttribute('title')||t.innerText||'').trim():''; if(ti)o.push({title:ti,author:u?u.innerText.trim():''});});
  return JSON.stringify(o.slice(0,40));})()""",
    },
    "kuaishou": {
        "name": "快手",
        "search": "https://www.kuaishou.com/search/video?searchKey={}",
        "hot": "https://www.kuaishou.com/rank",
        "js": """(()=>{const o=[];document.querySelectorAll('div[class*="video-card"], .search-card, a[href*="/short-video/"]').forEach(c=>{
  const t=c.querySelector('a[title], .title, [class*="title"]');
  let ti=t?(t.getAttribute('title')||t.innerText||'').trim():''; if(ti&&ti.length>2)o.push({title:ti,author:''});});
  return JSON.stringify(o.slice(0,40));})()""",
    },
    "weibo": {
        "name": "微博",
        "search": "https://s.weibo.com/weibo?q={}",
        "hot": "https://s.weibo.com/top/summary",
        "js": """(()=>{const o=[];document.querySelectorAll('td a, .td-01 a, .td-02 a').forEach(a=>{
  const ti=a.innerText.trim(); if(ti&&ti.length>1)o.push({title:ti,author:''});});
  return JSON.stringify(o.slice(0,40));})()""",
    },
    "zhihu": {
        "name": "知乎",
        "search": "https://www.zhihu.com/search?type=content&q={}",
        "hot": "https://www.zhihu.com/hot",
        "js": """(()=>{const o=[];document.querySelectorAll('.HotList-item, .ContentItem, a[class*="title"], h2 a').forEach(c=>{
  const t=c.querySelector('.HotList-itemTitle, a[class*="title"], h2 a, .ContentItem-title a');
  let ti=t?t.innerText.trim():c.innerText.trim(); if(ti&&ti.length>2)o.push({title:ti,author:''});});
  return JSON.stringify(o.slice(0,40));})()""",
    },
    "xiaohongshu": {
        "name": "小红书",
        "search": "https://www.xiaohongshu.com/search_result?keyword={}",
        "hot": "https://www.xiaohongshu.com/explore",
        "js": """(()=>{const o=[];document.querySelectorAll('.note-item, .cover, a[href*="/explore/"]').forEach(c=>{
  const t=c.querySelector('.title, [class*="title"]'); let ti=t?t.innerText.trim():c.getAttribute('title')||''; if(ti&&ti.length>2)o.push({title:ti,author:''});});
  return JSON.stringify(o.slice(0,40));})()""",
    },
    "baidu": {
        "name": "百度热搜",
        "search": "https://www.baidu.com/s?wd={}",
        "hot": "https://top.baidu.com/board?tab=realtime",
        "js": """(()=>{const o=[];document.querySelectorAll('.c-title a, .content_1Y6oW a, a[class*="title"], .title-content').forEach(a=>{
  const ti=a.innerText.trim(); if(ti&&ti.length>2)o.push({title:ti,author:''});});
  return JSON.stringify(o.slice(0,40));})()""",
    },
}

def http(u, timeout=15):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")

# 各平台登录页：用持久化 Chrome 配置打开，登录一次后搜索自动复用（解决抖音/快手/微博/知乎需登录态）
LOGIN_URLS = {
    "douyin": "https://www.douyin.com/login",
    "kuaishou": "https://www.kuaishou.com/profile/login",
    "weibo": "https://weibo.com/login.php",
    "zhihu": "https://www.zhihu.com/signin",
    "xiaohongshu": "https://www.xiaohongshu.com/login",
}

def launch_chrome():
    import subprocess
    cmd = [CHROME_EXE, "--remote-debugging-port=%d" % CDP_PORT,
           "--user-data-dir=%LOCALAPPDATA%\\ChromeDebug",
           "--no-first-run", "--no-default-browser-check"]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3); return True
    except Exception as e:
        print("启动 Chrome 失败：%s" % e); return False

def ws_version():
    try:
        return json.loads(http("http://127.0.0.1:%d/json/version" % CDP_PORT))["webSocketDebuggerUrl"]
    except Exception:
        return None

def new_tab_eval(url, js, wait=8):
    bws = ws_version()
    if not bws:
        if not launch_chrome(): return None
        bws = ws_version()
        if not bws: return None
    ws = websocket.create_connection(bws, timeout=40)
    def call(i, me, pa=None):
        ws.send(json.dumps({"id": i, "method": me, "params": pa or {}}))
        t0 = time.time()
        while time.time() - t0 < 30:
            try: m = json.loads(ws.recv())
            except Exception: return {}
            if m.get("id") == i: return m.get("result") or {}
        return {}
    tid = (call(1, "Target.createTarget", {"url": "about:blank"}) or {}).get("targetId")
    if not tid: return None
    sid = (call(2, "Target.attachToTarget", {"targetId": tid, "flatten": True}) or {}).get("sessionId")
    call(3, "Page.enable", None)
    ws.send(json.dumps({"id": 4, "method": "Page.navigate", "params": {"url": url}, "sessionId": sid}))
    time.sleep(wait)
    ws.send(json.dumps({"id": 5, "method": "Runtime.evaluate",
                        "params": {"expression": js, "returnByValue": True}, "sessionId": sid}))
    t0 = time.time(); val = None
    while time.time() - t0 < 14:
        try: m = json.loads(ws.recv())
        except Exception: break
        if m.get("id") == 5:
            val = ((m.get("result") or {}).get("result") or {}).get("value"); break
    try: ws.send(json.dumps({"id": 9, "method": "Target.closeTarget", "params": {"targetId": tid}}))
    except Exception: pass
    ws.close(); return val

def fetch(plat, mode, kw=""):
    cfg = PLATFORMS[plat]
    url = (cfg["hot"] if mode == "hot" else cfg["search"].format(urllib.parse.quote(kw)))
    print("  [%s] 打开 %s" % (cfg["name"], url))
    val = new_tab_eval(url, cfg["js"])
    items = []
    if val:
        try: items = json.loads(val)
        except Exception: pass
    return items

def analyze(items, kw, label=""):
    if not items:
        print("    ⚠ 未抽取到（可能需登录/页面结构变化/被反爬，建议换热榜模式或手动登录态）"); return 0
    print("    ✓ %s 抽到 %d 条" % (label or "结果", len(items)))
    ups = Counter((i.get("author") or "").strip() for i in items if i.get("author"))
    if ups:
        print("    — 活跃作者 TOP5 —")
        for u, c in ups.most_common(5): print("      %-20s %d 条" % (u[:20], c))
    words = Counter()
    for i in items:
        for w in re.findall(r"[一-龥A-Za-z0-9]{2,8}", i.get("title") or ""):
            words[w] += 1
    print("    — 高频词 TOP12 —")
    print("      " + "  ".join("%s(%d)" % (w, c) for w, c in words.most_common(12)))
    return len(items)

def open_login(plat):
    """用持久化 Chrome 配置打开平台登录页（登录一次后搜索自动复用）。"""
    import subprocess
    url = LOGIN_URLS.get(plat) or LOGIN_URLS["douyin"]
    ud = os.path.expandvars(r"%LOCALAPPDATA%\ChromeDebug")
    cmd = [CHROME_EXE, "--remote-debugging-port=%d" % CDP_PORT, "--user-data-dir=%s" % ud, url]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✓ 已用持久化配置打开 %s 登录页（%s）。登录后重跑搜索即可自动复用登录态。" % (plat, url))
    except Exception as e:
        print("打开失败：%s" % e)

def main():
    ap = argparse.ArgumentParser(description="全平台热点搜索/热榜/爬取分析器")
    ap.add_argument("cmd", choices=["hot", "search", "login"] + list(PLATFORMS.keys()))
    ap.add_argument("keyword", nargs="?", default="")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--all", action="store_true", help="search 模式下跨全部平台")
    a = ap.parse_args()

    if a.cmd == "login":
        if not a.keyword:
            print("用法：python vsearch.py login douyin|kuaishou|weibo|zhihu|xiaohongshu")
            return
        open_login(a.keyword); return

    if a.cmd == "hot":
        print("===== 实时热榜聚合 =====")
        total = 0
        for p in PLATFORMS:
            total += analyze(fetch(p, "hot"), "", PLATFORMS[p]["name"])
        print("热榜合计 %d 条" % total)
        return

    if a.cmd == "search":
        if a.all or not a.keyword:
            print("===== 关键词「%s」跨平台搜索 =====" % (a.keyword or "(空=各平台热榜)"))
            tot = 0
            for p in PLATFORMS:
                if not a.keyword and p in ("douyin", "kuaishou", "xiaohongshu", "tiktok"):
                    continue  # 这几个纯热榜需登录，跨搜跳过
                tot += analyze(fetch(p, "search", a.keyword), a.keyword, PLATFORMS[p]["name"])
            print("跨平台合计 %d 条" % tot)
            return
        # 单平台搜索走下面分支
        a.cmd = "bilibili" if not a.keyword else a.cmd

    # 单平台
    if a.cmd in PLATFORMS:
        if not a.keyword:
            print("请提供关键词，例如：python vsearch.py %s \"AI\"" % a.cmd); return
        print("===== %s 搜索「%s」=====" % (PLATFORMS[a.cmd]["name"], a.keyword))
        analyze(fetch(a.cmd, "search", a.keyword), a.keyword)

if __name__ == "__main__":
    main()
