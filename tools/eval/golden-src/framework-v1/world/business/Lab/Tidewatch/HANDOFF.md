# HANDOFF — Tidewatch

最后更新：2026-10-07 盘前

## 当前状态
- 实盘中（2026-09-21 起）。通知全部走 Discord；Wren 的 @mention 由 Relay（profile `tidewatch`）叫醒会话。
- 2026-10-06 收盘后上线「风险预算重构」，10-07 盘前重启 main.py 生效：
  - 风险预算固定 $20,000（`Config.RISK_BUDGET`），不再随账户 net_value 浮动
  - 每次入场的最大亏损 = 预算 × 5% = $1,000；张数 = 1,000 // 单张最大亏损
  - 09:20 ET premarket 记录 net_value（`PremarketValue`），只作参考
  - 16:10 ET wrapup：当日盈亏取券商的已实现盈亏（`broker.realized_pnl`），不再在 DB 里逐笔相加
  - flatten 早退：当天没有到期的 XLK/XLF 铁鹰时直接返回

## 待验证（实盘）
- [ ] premarket net_value 读取（09:20 ET）
- [ ] wrapup 取券商已实现盈亏
- [ ] 风险预算 $20,000 写进 DaySummary
- [ ] flatten 早退（无仓日）
- [ ] 5% sizing 的实际张数（要有入场的日子）
- [ ] flatten 真平仓（要有入场的日子）
- [ ] 非零已实现盈亏和券商对账单对得上（要有入场的日子）

## 已知问题
- broker 会话恢复（resume）后本地成交缓存是空的；对账要用服务器端的 fills。

## 下一步
- 有入场的交易日把上面剩下三项验完。
