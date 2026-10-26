#!/usr/bin/env python3
"""监控美国 Apple Store 附近门店的 iPhone 到店取货库存，有货时通过 Bark 推送到 iPhone。

只用 Python 标准库。所有配置都从环境变量读取：

  ZIP            必填，美国邮编（在 GitHub 上存成 Secret，避免出现在公开日志里）
  EXTRA_LOCATIONS 额外查询的邮编，逗号分隔，例如 10001,11201（Apple 每次只返回最近的 12 家店）
  BARK_KEY       必填，Bark App 里的设备 key（URL 里 https://api.day.app/ 后面那串）
  PARTS          要监控的型号，逗号分隔，默认 iPhone Duo 512GB 两种颜色
  INTERVAL       查询间隔秒数，默认 60
  DURATION       本次运行总时长秒数，默认 20700（5 小时 45 分，GitHub 单个任务上限 6 小时）
  MAX_MILES      只提醒这个距离以内的门店，默认 0 表示不限
  STATES         只提醒这些州的门店，逗号分隔，例如 NY；默认不限
  BARK_SERVER    Bark 服务器，默认 https://api.day.app
  BARK_LEVEL     Bark 通知级别：timeSensitive（默认）/ critical（静音也响）/ active
  TEST_NOTIFY    设为 true 时只发一条测试推送并查询一次库存，然后退出
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DEFAULT_PARTS = "MK1G4LL/A,MK1H4LL/A"  # iPhone Duo 512GB Star White / Night Sky
PART_NAMES = {
    "MK1G4LL/A": "iPhone Duo 512GB Star White",
    "MK1H4LL/A": "iPhone Duo 512GB Night Sky",
}
BUY_URL = "https://www.apple.com/shop/buy-iphone/iphone-duo"
# fulfillment-messages 接口会对 GitHub 服务器返回 541，旧的 pickup-message 接口可用
PICKUP_URL = "https://www.apple.com/shop/retail/pickup-message"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/18.0 Safari/605.1.15"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BUY_URL,
}
ERROR_ALERT_AFTER = 45 * 60  # 连续这么多秒没有一次查询成功，才推送“监控异常”
BLOCKED_BACKOFF = 5 * 60  # 被 Apple 限流（HTTP 541）后暂停这么多秒再试


def log(msg):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now}] {msg}", flush=True)


def env(name, default=None, required=False):
    value = os.environ.get(name, "").strip()
    if not value:
        if required:
            sys.exit(f"缺少环境变量 {name}")
        return default
    return value


def fetch_availability(zip_code, parts):
    """返回 (location, [store, ...])，每个 store 是 Apple 接口里的原始字典。"""
    query = {"pl": "true", "location": zip_code}
    for i, part in enumerate(parts):
        query[f"parts.{i}"] = part
    url = PICKUP_URL + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    body = data.get("body") or {}
    pickup = body.get("content", {}).get("pickupMessage") or body
    if pickup.get("errorMessage"):
        raise RuntimeError(f"Apple 返回错误：{pickup['errorMessage']}")
    stores = pickup.get("stores")
    if stores is None:
        raise RuntimeError(f"响应里没有 stores 字段：{json.dumps(data)[:300]}")
    return pickup.get("location") or zip_code, stores


def store_distance(store):
    for key in ("storedistance", "storeDistance"):
        try:
            return float(store[key])
        except (KeyError, TypeError, ValueError):
            pass
    return None


def available_items(stores, parts, max_miles, states=()):
    """返回 {(storeNumber, part): 描述字典}，只包含当前可取货的组合。"""
    found = {}
    for store in stores:
        dist = store_distance(store)
        if max_miles and dist is not None and dist > max_miles:
            continue
        if states and store.get("state") not in states:
            continue
        for part in parts:
            info = (store.get("partsAvailability") or {}).get(part)
            if not info or info.get("pickupDisplay") != "available":
                continue
            title = (info.get("storePickupProductTitle")
                     or ((info.get("messageTypes") or {}).get("regular") or {}).get("storePickupProductTitle")
                     or PART_NAMES.get(part, part))
            found[(store.get("storeNumber"), part)] = {
                "store": store.get("storeName") or store.get("storeNumber"),
                "city": store.get("city") or "",
                "distance": store.get("storeDistanceWithUnit") or (f"{dist} mi" if dist else ""),
                "title": title,
                "quote": info.get("pickupSearchQuote") or "",
            }
    return found


def bark(title, body, level=None, call=False):
    key = env("BARK_KEY", required=True)
    server = env("BARK_SERVER", "https://api.day.app").rstrip("/")
    payload = {
        "device_key": key,
        "title": title,
        "body": body,
        "group": "iPhone Duo",
        "url": BUY_URL,
        "level": level or env("BARK_LEVEL", "timeSensitive"),
    }
    if payload["level"] == "critical":
        payload["volume"] = 8
    if call:
        payload["call"] = "1"  # 铃声重复响 30 秒
        payload["sound"] = "alarm"
    req = urllib.request.Request(
        server + "/push", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            log(f"Bark 推送成功：{title}（{resp.status}）")
    except Exception as exc:  # 推送失败不应该让监控停下
        log(f"Bark 推送失败：{exc}")


def describe(item):
    parts = [item["title"], f"{item['store']}（{item['city']}）"]
    if item["distance"]:
        parts[-1] += f" {item['distance']}"
    if item["quote"]:
        parts.append(item["quote"])
    return " · ".join(parts)


def check_once(location, label, parts, max_miles, states):
    """查询一个位置，返回 (可取货 {(门店, 型号): 描述}, 本次返回的门店编号集合)。"""
    _, stores = fetch_availability(location, parts)
    found = available_items(stores, parts, max_miles, states)
    log(f"查询{label} {len(stores)} 家门店，可取货 {len(found)} 项")
    return found, {s.get("storeNumber") for s in stores}


def rotation(zip_code, extras):
    """每次只查一个位置，家附近和额外位置交替：家, 额外1, 家, 额外2, ...

    Apple 大约 20 分钟内收到 60 次请求就会限流 30 分钟，所以每分钟只发一次请求。
    """
    home = (zip_code, "家附近")
    if not extras:
        return [home]
    return [x for extra in extras for x in (home, (extra, extra))]


def main():
    zip_code = env("ZIP", required=True)
    extras = [z.strip() for z in env("EXTRA_LOCATIONS", "").split(",") if z.strip()]
    schedule = rotation(zip_code, extras)
    env("BARK_KEY", required=True)
    parts = [p.strip() for p in env("PARTS", DEFAULT_PARTS).split(",") if p.strip()]
    interval = int(env("INTERVAL", "60"))
    duration = int(env("DURATION", "20700"))
    max_miles = float(env("MAX_MILES", "0"))
    states = {s.strip().upper() for s in env("STATES", "").split(",") if s.strip()}
    log(f"开始监控 {', '.join(parts)}，每 {interval} 秒一次")

    if env("TEST_NOTIFY", "false").lower() == "true":
        try:
            found = {}
            for loc, label in dict(schedule).items():
                found.update(check_once(loc, label, parts, max_miles, states)[0])
            body = "\n".join(describe(i) for i in found.values()) or "当前附近门店都不能取货"
        except Exception as exc:
            body = f"查询 Apple 失败：{exc}"
        log(body)
        bark("iPhone Duo 监控测试", body)
        return

    notified = set()  # 已提醒过且仍有货的 (门店, 型号)，没货后移除，下次补货再提醒
    last_ok = time.monotonic()
    error_alerted = False
    step = 0
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        started = time.monotonic()
        wait = interval
        loc, label = schedule[step % len(schedule)]
        try:
            found, seen = check_once(loc, label, parts, max_miles, states)
            step += 1
            last_ok, error_alerted = time.monotonic(), False
            # 这次返回的门店里没货的组合移出 notified，别的位置的门店保持原状
            notified = {k for k in notified if k[0] not in seen or k in found}
            new = [found[k] for k in found if k not in notified]
            if new:
                for item in new:
                    log("有货：" + describe(item))
                bark(f"iPhone Duo 可取货！({len(new)} 项)",
                     "\n".join(describe(i) for i in new), call=True)
            notified |= set(found)
        except Exception as exc:  # 网络错误、被限流、格式变化都记下来继续跑
            blocked = isinstance(exc, urllib.error.HTTPError) and exc.code == 541
            if blocked:
                wait = BLOCKED_BACKOFF
            down = time.monotonic() - last_ok
            log(f"查询失败（已 {down / 60:.0f} 分钟没有成功）：{exc}"
                + ("，被限流，暂停 5 分钟" if blocked else ""))
            if down >= ERROR_ALERT_AFTER and not error_alerted:
                bark("iPhone Duo 监控异常", f"已 {down / 60:.0f} 分钟查询失败：{exc}", level="active")
                error_alerted = True
        time.sleep(max(0, wait - (time.monotonic() - started)))
    log("本次运行时间到，退出（工作流会自动接力下一次运行）")


if __name__ == "__main__":
    main()
