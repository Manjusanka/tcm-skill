# TCM Safe Knowledge QA Skill

一个面向中医知识库问答的可安装 Agent Skill，覆盖混合检索、知识图谱补充、受约束工具调用、记忆筛选、文档版本管理、证据化生成、医疗安全校验和分层评测。

> 本项目用于知识检索与工程示范，不提供医疗诊断、处方或个体化治疗建议。

## 特点

- 向量、关键词与图谱来源融合，先做权限/版本过滤，再做 RRF 与 rerank；
- 文档不可变版本、`ACTIVE` 发布指针与按 `logical_chunk_id` 的版本折叠；
- 工具白名单、参数校验、幂等与重试边界、标准化 `ToolResult`；
- 检索内容视为不可信数据，防止文档和工具结果中的提示词注入；
- 对剂量、禁忌、相互作用等高风险问题启用证据与人工升级要求；
- 提供 JSON Schema、冒烟评测集和可执行的一致性校验。

## 安装

将仓库克隆到 Codex skills 目录：

```bash
git clone https://github.com/Manjusanka/tcm-skill.git ~/.codex/skills/tcm-safe-knowledge-qa
```

也可以把整个目录复制到 `$CODEX_HOME/skills/tcm-safe-knowledge-qa`。重新启动或刷新 Codex 后，可通过 `$tcm-safe-knowledge-qa` 显式调用；默认也允许根据请求自动选择。

## 使用示例

```text
Use $tcm-safe-knowledge-qa to answer "正在服用华法林，能否自行加用含丹参的制剂？"
with current evidence, citations, and a safe disposition.
```

```text
使用 $tcm-safe-knowledge-qa 审计这条 RAG Trace，定位召回正确但最终答案错误的首个故障环节。
```

## 目录

```text
.
├── SKILL.md                         # Agent 入口与不可违反的规则
├── agents/openai.yaml               # Codex 展示与调用策略
├── skill.yaml                       # 可调工程参数
├── references/                      # 检索、工具、安全、评测和提示词细则
├── schemas/                         # 输入、工具结果和答案 JSON Schema
├── scripts/validate_package.py      # 包结构与参数约束校验
└── tests/test_package.py            # 契约测试
```

`skill.yaml` 中的 TopK、阈值和 Token 预算是生产方案的初始建议值，不代表任何特定系统的实测性能。应在目标语料、模型、硬件和风险分层评测集上重新标定。

## 校验

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_package.py
python -m unittest discover -s tests -v
```

Codex Skill 结构还可以使用官方 skill-creator 附带的 `quick_validate.py` 进行检查。

## 接入方式

本仓库定义逻辑工具能力，不绑定特定模型、向量库或 Agent 框架。接入时将本地服务映射为 `references/tools-and-agent.md` 中的工具族，并保证所有结果符合 `schemas/tool-result.schema.json`。模型、提示词、工具 Schema 和知识发布版本应分别记录，便于回滚和复现。

## License

[MIT](LICENSE)
