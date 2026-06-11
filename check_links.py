#!/usr/bin/env python3
"""
链接预筛脚本 — 批量检查URL是否能打开
用法：
  python3 check_links.py urls.txt           # 从文件读取URL，每行一个
  python3 check_links.py urls.txt --json     # 输出JSON格式
  echo "https://example.com" | python3 check_links.py -  # 从stdin读取

退出码：
  0 = 全部通过
  1 = 有失效链接
"""

import sys
import json
import urllib.request
import urllib.error
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

# 忽略SSL验证（某些网站证书有问题）
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

TIMEOUT = 10  # 秒


def check_url(url):
    """检查单个URL，返回结果字典"""
    url = url.strip()
    if not url or url.startswith("#"):
        return None

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        status = resp.getcode()
        return {
            "url": url,
            "ok": 200 <= status < 400,
            "status": status,
            "error": None,
        }
    except urllib.error.HTTPError as e:
        return {
            "url": url,
            "ok": False,
            "status": e.code,
            "error": f"HTTP {e.code}",
        }
    except urllib.error.URLError as e:
        return {
            "url": url,
            "ok": False,
            "status": None,
            "error": str(e.reason)[:100],
        }
    except Exception as e:
        return {
            "url": url,
            "ok": False,
            "status": None,
            "error": str(e)[:100],
        }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 check_links.py <urls.txt> [--json]")
        print("  urls.txt: 每行一个URL，#开头的行会被忽略")
        sys.exit(1)

    source = sys.argv[1]
    output_json = "--json" in sys.argv

    # 读取URL
    if source == "-":
        urls = [line.strip() for line in sys.stdin if line.strip()]
    else:
        with open(source, "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print("没有找到URL")
        sys.exit(0)

    # 并发检查（最多5个线程，避免被封）
    results = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(check_url, url): url for url in urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # 按原始顺序排序
    url_order = {url: i for i, url in enumerate(urls)}
    results.sort(key=lambda r: url_order.get(r["url"], 999))

    # 输出
    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count

    if output_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            status_icon = "✓" if r["ok"] else "✗"
            status_code = r["status"] or "N/A"
            error_msg = f" ({r['error']})" if r["error"] else ""
            print(f"  {status_icon} [{status_code}] {r['url']}{error_msg}")

        print(f"\n  总计: {len(results)} | 通过: {ok_count} | 失效: {fail_count}")

    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
