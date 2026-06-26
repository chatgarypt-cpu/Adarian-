# Adarian Report Agent

基于 Adarian ABM 舆情仿真输出，全自动生成面向政府决策者的舆情风险研判报告。

## 前置条件

- **Claude Code**（CLI 或 IDE 扩展）
- **Python 3.8+**（仅用于数据预处理脚本）

## 安装

将 `adarian-report-agent/` 文件夹拷入目标项目的 `.claude/skills/` 目录：

```
your-project/
└── .claude/
    └── skills/
        └── adarian-report-agent/
```

Claude Code 会自动加载该目录下的 Skill。

## 使用

```
/adarian-report <input_json_path>
```

调用后 Agent 会询问选择报告版本：

| 版本 | 字数 | 定位 |
|------|------|------|
| A 版 | 不限 | 自由生成，通读润色 |
| B 版 | 1,400-1,500 字 | 便捷速览 |
| C 版 | 3,800-4,000 字 | 详细阅读 |

支持单选或任意组合（如 B+C），多选时各版并发生成。

输入 JSON 格式详见 `references/input_spec.md`。输出结构、依赖说明、已知限制、完整文件地图见 [DELIVERY.md](DELIVERY.md)。

## 报告结构

- **一、舆情概要** — 事件事实陈述
- **二、演化分析** — 传播趋势与主体立场演化
- **三、风险研判** — 风险识别与证据校验
- **四、对策意见** — 风险锚定的对策建议
- **附录 A** — 仿真方法说明
- **附录 B** — 结构化数据

## 测试

在 adarian-report-agent 目录下执行：

```
python3 -m pytest scripts/test_build_appendix_b.py -q
# 若 python3 不存在，改用 python
```
