# TCM Safe Knowledge QA Skill

一个面向中医知识库问答的框架无关 Skill 内核，同时提供 Codex 适配入口。V2 将权限、路由、检索预算、工具副作用、上下文选择和引用校验从 Prompt 中抽离为可执行、可测试、可回放的控制面。

> 本项目用于知识检索与工程示范，不提供医疗诊断、处方或个体化治疗建议。

## V2 核心改进

- **框架无关内核**：`skill.yaml`、JSON Schema 和 stdin/stdout 脚本不依赖 Codex、LangGraph 或 Spring AI；
- **策略即代码**：模型负责开放语义，权限、急症、版本、写操作和重试由确定性策略裁决；
- **自适应检索预算**：按歧义、精确词、多跳、风险、证据缺口和系统负载动态分配 TopK；
- **两阶段工具网关**：先 Plan，再 Validate，最后 Execute，模型计划不直接等于外部命令；
- **Claim-Evidence 证据账本**：每个结论显式绑定 evidence ID、知识发布版本和内容哈希；
- **上下文编译器**：按单位 Token 的边际主张覆盖率选择证据，保持表格、剂量和否定表达原子性；
- **独立 Evidence Guard**：阻断未知引用、越权证据、旧版本证据和无权威来源的高风险主张；
- **可回放能力图**：记录策略版本、reason code、候选证据、工具轨迹和首个失败阶段。

详细的原问题、修改原因、实现方案和面试追问口径见：[Skill V2 改进说明与面试口径](docs/skill-v2-innovation-interview-guide.md)。

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

## 架构

```text
Framework Adapter
        ↓
Semantic Signals → Policy Engine → Capability Graph
                                      ├─ Retrieval / Graph / Memory
                                      └─ Tool Plan → Validate → Execute
                                                    ↓
Evidence Ledger → Context Compiler → Generator → Evidence Guard → Response
```

`SKILL.md` 和 `agents/openai.yaml` 只是 Codex Adapter。框架无关接口见 [Framework-neutral architecture](references/framework-neutral-architecture.md)。

## 目录

```text
.
├── SKILL.md                         # Agent 入口与不可违反的规则
├── agents/openai.yaml               # Codex 展示与调用策略
├── skill.yaml                       # 框架无关清单、策略与工程参数
├── docs/                             # V1问题、V2改进和面试口径
├── references/                      # 能力图、检索、工具、安全和评测细则
├── schemas/                         # 输入、语义特征、决策、证据和答案契约
├── scripts/
│   ├── policy_engine.py             # 确定性路由与风险裁决
│   ├── adaptive_retrieval.py        # 自适应检索预算
│   ├── context_compiler.py          # 边际覆盖上下文选择
│   ├── tool_gateway.py              # 工具计划、租户、副作用与幂等校验
│   ├── evidence_guard.py            # Claim-Evidence 独立校验
│   └── validate_package.py          # 包结构与跨字段校验
└── tests/                            # 契约与核心策略测试
```

`skill.yaml` 中的 TopK、阈值和 Token 预算是生产方案的初始建议值，不代表任何特定系统的实测性能。V2 的创新属于工程组合创新，不宣称已经完成医疗生产验证；所有参数都应在目标语料、模型、硬件和风险分层评测集上重新标定。

## 校验

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_package.py
python -m unittest discover -s tests -v
```

策略演示：

```bash
echo '{"risk_flags":["drug_interaction"],"requires_fresh_data":true,"confidence":0.95}' \
  | python scripts/policy_engine.py
```

Codex Skill 结构还可以使用官方 skill-creator 附带的 `quick_validate.py` 进行检查。

## 接入方式

本仓库定义逻辑工具能力，不绑定特定模型、向量库或 Agent 框架。接入时将本地服务映射为 `references/tools-and-agent.md` 中的工具族，并保证所有结果符合 `schemas/tool-result.schema.json`。模型、提示词、策略、工具 Schema 和知识发布版本应分别记录，便于回滚和复现。

## License

[MIT](LICENSE)
