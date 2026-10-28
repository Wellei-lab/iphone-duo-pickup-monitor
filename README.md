# iPhone Duo 取货监控

在 GitHub Actions 上每 60 秒查询一次附近美国 Apple Store 的到店取货（Pickup）库存，有货时通过 [Bark](https://bark.day.app) 推送到 iPhone，铃声连响 30 秒。

默认监控 iPhone Duo 512GB 两种颜色：

| 型号 | 颜色 |
|---|---|
| MK1G4LL/A | Star White |
| MK1H4LL/A | Night Sky |

型号来自零售商页面，尚未在 Apple 官网核实。若跑起来日志里一直是“可取货 0 项”但官网显示有货，请到 apple.com 的取货页面确认型号，再改 `PARTS` 变量。

## 设置（只需一次）

1. iPhone 从 App Store 安装 **Bark**，打开后复制示例 URL 里 `https://api.day.app/` 后面那串 key。
2. 仓库 **Settings → Secrets and variables → Actions**：
   - **Secrets** 新建 `BARK_KEY` = 上一步的 key
   - **Secrets** 新建 `ZIP` = 你的美国邮编（用 Secret 而不是 Variable，公开仓库的运行日志所有人可见，Secret 会被打码）
   - 可选 Variables：
     - `MAX_MILES`：只提醒多少英里以内的门店，默认 `35`，填 `0` 表示不限
     - `STATES`：只提醒哪些州的门店，默认 `NY`（排除长岛对岸的康涅狄格州门店）
     - `EXTRA_LOCATIONS`：额外查询的邮编，默认 `10001`（曼哈顿）。Apple 每次只返回最近的 12 家店，加上曼哈顿能覆盖纽约市除 Staten Island 外的 11 家
     - `INTERVAL`：非高峰时段的请求间隔秒数，默认 `75`
     - `INTERVAL_PLAN`：按纽约时间分时段的请求间隔，默认 `8-11:60`（早上 8–11 点 60 秒）。试过早高峰 45 秒，约 40 分钟就被限流 30 分钟，不划算
     - `QUIET_HOURS`：纽约时间完全暂停查询的时段，例如 `2-8`；默认不设，全天监控（凌晨 1 点多也出现过补货）
     - `PARTS`：改监控型号，逗号分隔
     - `BARK_LEVEL`：`critical` 表示静音/专注模式下也响（需要在 Bark 里允许重要提醒）
3. **Actions** 页面 → 左侧 *iPhone Duo pickup monitor* → **Run workflow**，勾选 `test_notify` 运行一次。手机收到“iPhone Duo 监控测试”就说明推送和 Apple 查询都通了。
4. 再 **Run workflow** 一次（不勾任何选项），正式开始监控。

## 运行方式

- 每次只查一个位置，轮流查“家附近 → 曼哈顿 10001”。纽约时间 8–11 点每 60 秒一次请求（每家店约 2 分钟查一次），其余时间每 75 秒一次（每家店约 2.5 分钟）。全天不暂停。
- 为什么不每分钟查所有位置：实测每分钟 3 次请求时，Apple 大约 20 分钟（约 60 次请求）后返回 HTTP 541 限流 30 分钟，如此循环。
- 遇到 541 限流或 503 服务不可用时暂停 5 分钟再试；超过 45 分钟一次都没成功才推送“监控异常”。
- 每轮任务循环约 5 小时 45 分（GitHub 单任务上限 6 小时）；结束时自动启动下一轮。
- 定时任务每 20 分钟兜底检查一次：如果监控没在跑就启动，已经在跑就直接跳过。
- 同一门店同一型号只在“没货 → 有货”时提醒一次；卖光后再补货会再次提醒。
- 有货推送：标题写门店和颜色（如“有货！Smith Haven · Night Sky 512GB”），铃声连响 30 秒，点开直接进入这一款的购买页（试过直接打开购物袋，但购物袋报错打不开，已改回）。
- 卖光后再推一条“已售罄：门店 · 颜色”，写上货大约留了几分钟（按查询间隔估算，误差约 2 分钟）。
- 实测（2026-10-27）：纽约时间 9:31–9:48 有一波 Night Sky 512GB 补货，6 家店每家只留了 1–3 分钟。
- 实测（2026-10-28，纽约时间，全部是 Night Sky 512GB，每次 2–4 分钟售罄）：
  - 凌晨 1:12 Smith Haven、1:18 Queens Center
  - 早上 8:46 SoHo + Fifth Avenue、9:32 Manhasset、9:38 Roosevelt Field、9:45 Williamsburg、10:10 The Mall at Bay Plaza
  - 被限流：4:23 起 30 分钟（541）、8:59 起约 5 分钟（541，随后换新一轮）、12:40 起约 30 分钟（503）

## 停止

Actions 页面 → *iPhone Duo pickup monitor* → 右上角 **⋯ → Disable workflow**，再取消正在运行的任务。

## 注意

- 公开仓库的 GitHub Actions 免费；不要改成私有仓库，私有仓库每月免费 2000 分钟，不够全天运行。
- 请求太频繁时 Apple 会返回 HTTP 541 限流。不要把 `INTERVAL` 调得比 60 秒更短，也不要加太多 `EXTRA_LOCATIONS`。
- 把 Actions 当成长时间运行的监控器不完全符合 GitHub 的使用条款，个人短期抢购用问题不大，买到后请停用。
