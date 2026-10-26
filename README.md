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
     - `INTERVAL_PLAN`：按纽约时间分时段的查询间隔，默认 `0-6:120,6-11:45`（夜里 120 秒，早上高峰 45 秒，其余 60 秒）
     - `PARTS`：改监控型号，逗号分隔
     - `BARK_LEVEL`：`critical` 表示静音/专注模式下也响（需要在 Bark 里允许重要提醒）
3. **Actions** 页面 → 左侧 *iPhone Duo pickup monitor* → **Run workflow**，勾选 `test_notify` 运行一次。手机收到“iPhone Duo 监控测试”就说明推送和 Apple 查询都通了。
4. 再 **Run workflow** 一次（不勾任何选项），正式开始监控。

## 运行方式

- 每分钟只向 Apple 发 1 次请求，轮流查“家附近 → 曼哈顿 10001”，每家店每 2 分钟查一次。纽约时间 0–6 点放慢到 2 分钟一次请求。
- 为什么不每分钟查所有位置：实测每分钟 3 次请求时，Apple 大约 20 分钟（约 60 次请求）后返回 HTTP 541 限流 30 分钟，如此循环。
- 遇到 541 限流时暂停 5 分钟再试；超过 45 分钟一次都没成功才推送“监控异常”。
- 每轮任务循环约 5 小时 45 分（GitHub 单任务上限 6 小时）；结束时自动启动下一轮。
- 定时任务每 20 分钟兜底检查一次：如果监控没在跑就启动，已经在跑就直接跳过。
- 同一门店同一型号只在“没货 → 有货”时提醒一次；卖光后再补货会再次提醒。

## 停止

Actions 页面 → *iPhone Duo pickup monitor* → 右上角 **⋯ → Disable workflow**，再取消正在运行的任务。

## 注意

- 公开仓库的 GitHub Actions 免费；不要改成私有仓库，私有仓库每月免费 2000 分钟，不够全天运行。
- 请求太频繁时 Apple 会返回 HTTP 541 限流。不要把 `INTERVAL` 调得比 60 秒更短，也不要加太多 `EXTRA_LOCATIONS`。
- 把 Actions 当成长时间运行的监控器不完全符合 GitHub 的使用条款，个人短期抢购用问题不大，买到后请停用。
