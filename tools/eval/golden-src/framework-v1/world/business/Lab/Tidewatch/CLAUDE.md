# Tidewatch

Wren 的期权卖方机器人：0DTE iron condor（XSP、XLK、XLF）。2026-09-21 起实盘。

## 运行
- Wren 在自己的终端里跑 `python main.py`（不是会话的后台任务）。进程里有调度器（APScheduler
  BackgroundScheduler，任务在工作线程里跑）和一个本地状态接口（`127.0.0.1:8765/status`）。
- 日志：`logs/tw_<本地日期>.log`，时间戳是本机时间（PT）。
- 券商：`broker/client.py`，进程里只有一个 broker 会话，启动时打开。
- 状态和待验证项：`HANDOFF.md`。

## 每日任务（cron 用 ET，日志里是 PT）

| ET | PT | 任务 | 通知 |
|---|---|---|---|
| 09:20 | 06:20 | premarket：经济日历 blackout、记录 net_value | blackout 时发 |
| 10:05 | 07:05 | entry_am：上午入场（VIX1D 高于上限就不开） | 每笔入场一条 |
| 13:00 | 10:00 | entry_pm：下午入场 | 每笔入场一条 |
| 15:45 | 12:45 | flatten：XLK/XLF 铁鹰收盘前全部平掉，防行权 / pin | FLAT 报告一条 |
| 16:10 | 13:10 | wrapup：XSP 现金结算 + 日终复盘 | 日终复盘一条 |

XSP 是欧式现金结算，不进 flatten，16:10 wrapup 处理。

## 通知
- 全部走 Discord：`notify/discord.py::send_discord`（2026-09-30 从邮件提醒切过来，邮件通道已删）。
- Wren 在 Discord 上 @Tidewatch 时，由 Relay（`../Relay/`，profile `tidewatch`）叫醒会话。

## 经济日历
`data/economic_calendar.py`：FOMC 决议日、CPI、非农。这些日子整天不入场。
只收录这三类，其他（官员讲话、会议纪要等）不在表里。

## 规则
- 实盘代码改动：收盘后改，第二天盘前重启 main.py 生效。
- 涉及资金的结论以券商成交和已实现盈亏为准，不以 DB 推断。
