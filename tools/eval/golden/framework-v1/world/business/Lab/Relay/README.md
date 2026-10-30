# Relay

Wren 自己写的 Discord 机器人，用来在 Discord 上叫醒正在跑的 Claude Code 会话。

## 怎么工作
1. Claude Code 会话用后台任务启动 `listener.py`（会话不阻塞，进程常驻）。
2. listener 连上 Discord，上线时往 stdout 打一行 `RELAY_READY <bot>`。
3. 有人 @机器人 时，listener 把消息追加到 `inbox/<profile>.jsonl`，同时往 stdout 打一行
   `MENTION <msg_id> | <author> | <content>`。后台任务的这行输出会作为事件通知送进会话，会话被唤醒。
4. 会话用 `cli.py drain` 读出收件箱，在当前会话里处理（读代码、查日志、改东西都行），
   再用 `cli.py send <file> <channel_id>` 把回复发回 Discord。

不调用任何 LLM API。处理消息的就是当前这个 Claude Code 会话本身。

## 文件
- `listener.py`：discord.py 客户端，只做监听和落盘
- `cli.py`：`drain`（读并清空收件箱）、`send`（用 bot token 发消息）
- `profiles.toml`：每个用途一个 profile（频道、bot 名）
- token 从环境变量 `RELAY_BOT_TOKEN` 读，不进仓库

## 用法
```
python listener.py --profile tidewatch          # 后台任务里跑
python cli.py drain --profile tidewatch
python cli.py send tmp/reply.txt <channel_id> --profile tidewatch
```
