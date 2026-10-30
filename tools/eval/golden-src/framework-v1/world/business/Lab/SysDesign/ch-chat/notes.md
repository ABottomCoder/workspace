# ch-chat · 聊天系统

定位：Messenger 式聊天系统，5000 万 DAU。WebSocket 长连接 + 有状态 chat server + KV 存聊天记录 + 心跳维护在线状态。

## 需求与估算

- 1 对 1 + 群聊（上限 100 人）；只做文本，单条 ≤ 100,000 字符；聊天记录永久保存。
- 在线状态；多设备同时登录；离线推送通知；端到端加密暂不要求。
- 1M 并发连接 × 每连接约 10KB ≈ 10GB：一台机器理论上装得下，但单机是单点故障，只能当起点。

## 服务器怎么推消息

| 技术 | 机制 | 缺陷 |
|---|---|---|
| 轮询 | 客户端定期问"有新消息吗" | 大多数请求的答案是"没有"，白耗资源 |
| 长轮询 | 服务端 hold 住连接直到有消息或超时 | 收发双方可能连在不同服务器上；服务端感知不到客户端断开 |
| WebSocket | 从 HTTP 握手升级而来，双向、持久 | 服务端要做连接管理 |

## 系统切三块

- 无状态服务：登录、注册、资料、服务发现查询。普通 HTTP，前面挂 LB。
- 有状态服务：chat server，客户端和它保持 WebSocket 长连接。
- 第三方集成：离线推送通知。

## 架构图

```
选址链路（HTTP）：  客户端 → LB → API servers → 服务发现 (ZooKeeper) → 返回 "去连 chat-server-7"
聊天链路（WebSocket）：客户端 ⇄ chat server（直连）
chat server 背后：  chat server → ID 生成器
                    chat server → 消息同步队列 → KV 存储（聊天记录）
                    chat server → presence servers（在线状态）
                    chat server → 推送通知（收件人离线时）
```

## 为什么 chat service 有状态

每个客户端与某台 chat server 之间是持久连接，只要那台服务器活着，客户端就不会换。连接本身就是状态。这决定了：不能用普通 LB 随机路由，要靠服务发现分配并配合容量控制；chat server 挂了由 ZooKeeper 重新指派新服务器重连。登录、资料等非实时功能仍走无状态 HTTP。

## 有 LB 为什么还要 ZooKeeper

- LB 是数据面的每请求转发器：服务无状态，选错了下个请求换一台即可，流量一直穿过它。
- 服务发现是控制面的一次性选址：为一条要活几小时的 WebSocket 按地理、容量、负载挑落点，客户端拿到地址后直连 chat server，流量不再经过它。
- ZooKeeper 的第二个职责 LB 给不了：全局成员视图。它是宕机后重连重分配的入口，而且服务于所有组件；LB 的健康检查只是局部踢名单。

## chat server 宕机

1. 检测：客户端心跳超时；chat server 在 ZooKeeper 上的 ephemeral node 随会话断开自动删除。
2. 客户端重新走选址链路，服务发现按最新的存活名单和容量分配新 server。
3. 客户端带着 cur_max_message_id 连上新 server，从 KV 补拉错过的消息。

## 1 对 1 消息流

1. 用户 A 把消息发给 chat server 1。
2. chat server 1 从 ID 生成器拿到 message_id。
3. chat server 1 把消息发进消息同步队列。
4. 消息存进 KV 存储。
5. 如果 B 在线，消息转发到 B 所连的 chat server 2。
6. 如果 B 离线，推送服务发通知。
7. chat server 2 通过 WebSocket 把消息推给 B。

## 存储

- 聊天记录用 KV store（量大、只有最近的被高频访问、读写比约 1:1、要水平扩展）。资料、好友等通用数据留在关系库。
- 1 对 1 表主键 message_id；群聊复合主键 (channel_id, message_id)，channel_id 做分区键。
- 消息顺序靠 message_id（唯一、按时间可排序），不靠 created_at。只要求会话内有序，每个 channel 一个本地序列号就够。

## 多设备同步

每台设备各自维护 cur_max_message_id。"新消息" = 收件人是当前用户且 message_id > 本设备的 cur_max_message_id。各设备独立从 KV 拉增量，不需要设备间协调。

## 群聊

- 小群（≤ 100）：A 发一条群消息，复制进每个成员的消息同步队列（inbox）。写放大换读简单，每人只看自己的 inbox。
- 大群不能这样做，这也是题目限定 100 人的原因。大群切读扩散：消息只存一份在群的时间线 (channel_id, seq) 里，成员各自带游标读。这和 news feed 里大 V 的处理是同一个问题。

## 在线状态

- 登录时写 online + last_active_at，登出改 offline。
- 难点是网络抖动：过隧道频繁断连，断开就变灰会闪烁。用心跳：客户端每 5 秒一次，30 秒内收到过就算在线。
- 状态变化经 pub-sub 广播：每对好友一条 channel，A 的状态变化发布到 A-B、A-C、A-D，好友各自订阅。
- 小群有效；10 万人的群一次变更就是 10 万个事件，应改为进群时或手动刷新时再拉取。

## 易错点

- 一上来就说 WebSocket，讲不出轮询、长轮询各自为什么被淘汰。
- 用 created_at 排序消息。
- 在线状态做成"断开即离线"，答不出心跳。
- 聊天记录放关系库，说不清 KV 的理由。
- 忽略多设备同步。
- 单机装得下 1M 连接就真设计成单机。
