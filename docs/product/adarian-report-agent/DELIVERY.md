# Adarian Report Agent — 交付说明

## 项目定位

基于 Adarian ABM 舆情仿真输出，全自动生成面向政府决策者的舆情风险研判报告。

## 安装

将 `adarian-report-agent/` 文件夹拷入目标项目的 `.claude/skills/` 目录：

```
your-project/
└── .claude/
    └── skills/
        └── adarian-report-agent/
```

Claude Code 启动时自动加载。无需额外配置或环境变量。

## 使用

```
/adarian-report <input_json_path>
```

Agent 会首先询问选择报告版本：

| 版本 | 字数 | 定位 |
|------|------|------|
| A 版 | 不限 | 自由生成，通读润色 |
| B 版 | 1,400-1,500 字 | 便捷速览 |
| C 版 | 3,800-4,000 字 | 详细阅读 |

支持单选或任意组合（如 B+C）。多选时各版并发生成。

## 输入

上游提供单个 JSON 文件，格式见 `references/input_spec.md`。核心字段：

```json
{
  "event_name": "OPPO母亲节文案事件",
  "seed_input_path": "./seed_input.txt",
  "worlds": [
    {
      "label": "world_0",
      "simulation_dataset_path": "./world_0/simulation_dataset.json"
    }
  ]
}
```

- `event_name`：事件名称，同时用作报告标题
- `seed_input_path`：事件原始材料（.txt），相对路径相对于 input JSON 所在目录
- `worlds`：至少 1 个 world，多 world 时自动聚合（均值 + 分布 + 最坏合理等级）

## 输出

每份报告提供两个文件：`_含附录.md`（正文 + 附录 A + 附录 B）和 `_无附录.md`（仅正文）。

多版本时（如 B+C）输出结构：

```
./reports_output/
└── [安全事件名]/
    ├── appendix_b.json                   ← 共享数据报告
    ├── B版/
    │   ├── *_无附录.md
    │   └── *_含附录.md
    └── C版/
        ├── *_无附录.md
        └── *_含附录.md
```

单选时省略版级目录，两份 `.md` 直接放在 `[安全事件名]/` 下。

报告结构：一、舆情概要 → 二、演化分析 → 三、风险研判 → 四、对策意见 → 附录 A（方法论）→ 附录 B（结构化数据）。

## 依赖

- **Python 3.8+**（仅 `build_appendix_b.py` 数据预处理脚本需要）
- **Claude Code**（CLI 或 IDE 扩展）

## 测试

在 adarian-report-agent 目录下执行：

```
python3 -m pytest scripts/test_build_appendix_b.py -q
# 预期输出：95 passed in ~0.2s
# 若 python3 不存在，改用 python
```

## 已知限制

1. **Agent 沙箱限制 Python 执行**：后台 Agent（并发版）无法可靠执行 Python 脚本。T3 字数统计使用 LLM 自估（偏差约 ±5%），非精确计数。`scripts/count_chars.py` 仅供手动调试时使用。
2. **Windows bash 中文编码**：Git Bash 终端 stdout 与 Python UTF-8 输出不兼容，中文可能显示为乱码。产品文件（.md/.json）UTF-8 读写正常。开发调试时优先使用 Read 工具查看中文内容。
3. **LLM 自估字数偏差**：T3 逐章生成时靠 LLM 自估字数判断是否需要扩充/删减，偏差通常 ±5%。"建议首稿"中位数锚定是达标核心因素。
4. **T2 Python 脚本编码**：`.py` 脚本首行必须有 `# -*- coding: utf-8 -*-` 声明；脚本中避免中文弯引号（U+201C/U+201D），使用 ASCII 直引号或中文括号替代。
5. **输入 JSON 引号**：`event_name` 中如有中文引号，使用弯引号 ""（U+201C/U+201D），避免 ASCII 直引号与 JSON 字符串分隔符冲突。

## 文件地图

| 文件 | 用途 |
|------|------|
| `SKILL.md` | Skill 入口，LLM 流程编排（T0→T4） |
| `README.md` | 快速入门 |
| `scripts/build_appendix_b.py` | 数据预处理：聚合、过滤、风险校验 |
| `scripts/count_chars.py` | 中文字数精确统计（手动调试用） |
| `scripts/test_build_appendix_b.py` | 测试（95 passed） |
| `references/input_spec.md` | 输入 JSON 正式 schema |
| `references/appendix_a.md` | 附录 A 固定文本（五章方法论） |
| `references/appendix_b_schema.yaml` | 附录 B 输出白名单（机器审计） |
| `references/aggregation_config.yaml` | 多 world 聚合规则 |
| `references/evolution_calc.md` | 演化分析计算规则 |
| `references/risk_rules.yaml` | 风险打标规则（机器可读） |
| `references/risk_rules.md` | 风险打标规则（LLM 阅读） |
| `references/risk_mapping.yaml` | 风险映射表（6 域 28 类） |
| `references/countermeasure_templates.yaml` | 对策模板库 |
| `references/writing_guide.md` | 文字报告写作规范 |
| `references/quality_checklist.yaml` | 自动化审核清单（5 类） |
| `references/dataset_fields.yaml` | 上游字段规格（34 条） |

## 开发历史

- v1.0：Phase 1-5 完整开发与测试（2026-06-11 ~ 2026-06-26）
- 18 轮集成测试（test1→test14），三版（A/B/C）并发架构稳定
- 确定性验证通过：risk_match / level_match / ref_match 三锚点 100% 一致
- 基线：95 条测试，零回归
