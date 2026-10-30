# helpdesk — Ferrowick AI 工单分类助手

## 是什么
给 Ferrowick 客服团队用的工单助手：工单进来 → LLM 分类（延误 / 破损 / 改址 / 账单 / 其他）、提取运单号、
起草回复 → 客服审核后发出。

## 技术栈
- 后端 FastAPI（`app/`），前端 React（`web/`）
- Postgres（AWS RDS，us-east-1），附件存 S3（us-east-1）
- LLM：`app/llm/providers.py`。现在用 Anthropic API；另有一个 OpenAI 兼容格式的 provider，写好了但没启用
- 部署：AWS ECS Fargate，us-east-1。AWS 账号归 Ferrowick，由 Lee Park 管

## 数据
- 工单正文里有收件人姓名、电话、收货地址、运单号；部分附件是签收照片
- 历史工单约 30 万条，涉及约 18 万个美国收件人
- 客户的口径：数据只放在客户自己的 AWS 账号里；新增任何第三方数据处理方，要 Lee Park 书面同意（合同附件 B）

## 状态（2026-10-20）
- v1 在客户内部试用，分类准确率 93%（4 类测试集）
- 月度模型调用费约 $1,900，Dana 说他们老板嫌贵
- 下一步：成本优化；客户要的第二阶段（自动回复）还没报价
