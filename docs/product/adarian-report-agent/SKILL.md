---
name: adarian-report-agent
description: 消费 Adarian ABM 舆情仿真数据，全自动生成面向政府决策者的舆情风险研判报告。触发场景：用户要求生成舆情报告、风险研判报告，或使用 /adarian-report 命令。适用于消费仿真 JSON 数据产出结构化舆情分析报告的任何场景。
---

# Adarian Report Agent

消费上游仿真 JSON，全自动生成舆情风险研判报告。数据传递全程同一上下文完成（全内存直传 + 附录 B JSON 固化防偏移），不 spawn 子 agent 做数据处理。B/C 两版文字报告的生成可在 T2 完成后并发 Agent 执行以提升效率。

## 触发

```
/adarian-report <input_json_path>
```

`input_json_path` 是上游同事提供的 JSON 文件，格式见 `references/input_spec.md`。内含 `event_name`、`seed_input_path`、`worlds` 列表。

**调用后首先询问用户**：选择 A 版（无字数要求，自由生成）、B 版（便捷速览，正文 1400-1500 字）、C 版（详细阅读，正文 3800-4000 字），可单选也可任意多选（如 A+B、B+C、A+B+C 等）。多选时 T2 后并发 Agent 同时生成各版本。字数规格见 `references/writing_guide.md`。

## 全链路流程

分五个阶段执行。每阶段只 Read 该阶段需要的 references/ 文件，读完即用，用完即抛。

### T0 — 校验输入

1. Read input JSON → 解析 `event_name`、`seed_input_path`、`worlds` 列表
2. 校验 `seed_input_path` 存在且可读，缺失则阻断报错
3. 校验每个 world 的 `simulation_dataset_path` 存在且可读，缺失则阻断报错
4. 生成 `safe_event_slug`：LLM 根据 `event_name` 提炼简短概括（如"OPPO母亲节文案争议"），用作目录名和文件名前缀。仅保留核心主体 + 核心事件，去除修饰语、标点、副标题，控制在 20 字以内。再将 `/ \ : * ? " < > |` 替换为 `_`

### T1 — 演化分析 + 风险证据提取

1. Run `scripts/build_appendix_b.py --mode evolution --input <input_json_path> --output ./reports_output/<slug>/appendix_b.json`
2. Read `references/evolution_calc.md` → 核验脚本输出的聚合结果合理性
3. 脚本产出 `appendix_b.json` 含 `meta` + `evolution_analysis` + `source_evidence` 三个顶层 key

**锚点 1**：appendix_b.json 在 T1 完成后立即写入磁盘，不拖延。

### T2 — 风险打标 + 对策生成

> 此阶段由 LLM 在上下文中执行（读取规则 YAML → 推理 → 写 JSON），不调用外部脚本。
> `scripts/build_appendix_b.py --mode risk` 为 deep validate-only：T2 风险打标与对策生成由 LLM 在上下文中完成，脚本不生成也不覆盖内容，只校验 `risk_assessment` / `countermeasures` 的完整字段、无确认风险例外分支和风险-对策闭环。

1. Read `appendix_b.json`（evolution_analysis + source_evidence 分支）
2. Read `references/risk_rules.yaml` + `references/risk_mapping.yaml`
3. 执行两层风险打标：
   - **类型候选层**：从 `source_evidence.worlds[].risk_type_classification.primary_types` 提取候选风险类型
   - **证据校验层**：交叉校验 `source_evidence.worlds[].risk_verdict.signals` + `evolution_analysis.emotion_trajectory` + `evolution_analysis.agent_stance_matrix` + `evolution_analysis.event_scale_avg/distribution` + `evolution_analysis.event_controversy_avg/distribution`
4. 证据不足时降级或输出保守标签，不强行补足三条；通常应确认 1-3 条风险，只有证据确实不足以确认任何风险时，才允许 `risks=[]` + `no_confirmed_risks_reason` + `measures=[]`
5. Read `references/countermeasure_templates.yaml` → 为每条确认风险匹配对策骨架（A+B+C：风险锚定 + 责任主体 + 行动方向）；每条非 supporting 对策必须复用配对 `risk_label`，并写入 `trigger_reason_ref`、`level_id_ref`。**关键约束**：`trigger_reason_ref` 和 `level_id_ref` 必须逐字复制配对风险的 `trigger_reason` 和 `level_id` 字段值，不得改写或摘要，否则 `--mode risk` 校验将报错
6. 将风险打标与对策结果写入 `appendix_b.json`：使用 Write 工具创建一个 Python 脚本（如 `_t2_append.py`），在脚本中直接以 Python dict/list 字面量构建 `risk_assessment`（内含 `risks` 数组，不是 `confirmed_risks`）和 `countermeasures`（内含 `measures` 数组）。中文内容全部嵌入 Python 字符串字面量。脚本逻辑：`json.load` 读取现有 appendix_b.json → 将 Python 字面量构建的 risk_assessment 和 countermeasures 赋值到 dict → `json.dump` 写回。执行 `python3 _t2_append.py`（若 `python3` 不存在，改用 `python _t2_append.py`）完成合并，完成后删除脚本。精确 key 名见 `references/appendix_b_schema.yaml`。禁止：① `bash -c` 内联 Python（所有平台，shell 转义不可控）；② 中文内容写入独立 JSON 文件后再由 Python 读回（跨平台/跨工具链时中文弯引号在 JSON 字符串值内可能被破坏；Python 字符串字面量不经过 JSON 编解码，无此风险）。**Python 脚本编码要求**：③ 含中文的 `.py` 文件首行（或第二行，在 shebang 之后）必须加 `# -*- coding: utf-8 -*-`，防止 Windows Python 按系统编码（GBK）误读 UTF-8 源码；④ 脚本内中文弯引号 `“` `”`（U+201C/U+201D）一律替换为 ASCII 直引号 `'...'` 或中文括号 `（...）`——弯引号在 Windows Python 解析器中可能触发 SyntaxError（字节边界错位）

### T2.5 — 版本分发

T2 完成后根据用户选择分发：

**若用户选择单一版本**（A 版、B 版或 C 版）：直接进入下方 T3，在当前上下文串行执行。A 版跳过所有字数目标和统计步骤。

**若用户选择多个版本**（如 A+B、B+C、A+B+C 等）：T2 已产出 `appendix_b.json`，各版本 T3+T4 输入同源、输出独立，可完全并发。为每个所选版本启动一个后台 Agent：

1. 为每个版本构建一份 Agent prompt，各自包含：
   - 版本标识（A / B / C）及对应字数目标（A: 无要求 / B: 1400-1500 / C: 3800-4000）
   - `appendix_b.json` 路径、`seed_input` 路径
   - 输出目录（`./reports_output/<slug>/<版本>/`，如 `./reports_output/<slug>/A版/`）
   - 下方 T3（逐章生成）和 T4（审核+拼接）的完整指令
   - 需读取的 references 文件路径：`adarian-report-agent/references/writing_guide.md`、`adarian-report-agent/references/quality_checklist.yaml`、`adarian-report-agent/references/appendix_a.md`
2. 同时调用 Agent 工具（`subagent_type="general-purpose"`, `run_in_background=true`），各 Agent 各自独立执行 T3→T4
3. 等待全部完成。任一个失败则报告失败原因但不阻断成功方输出；**全部成功才标记全链路完成**
4. 汇总各版本结果，向用户报告每个版本的产出路径和审核结果
5. 并发路径完成后 **skip T3 和 T4**（已由 Agent 执行）

---

### T3 — 文字报告生成（逐章生成，自估字数精调）

> **A 版（无字数要求）**：跳过下方所有字数目标，四章自由生成后直接通读润色。仅遵守各章写作规则和禁止项。
>
> **B 版 / C 版**：严禁一次性生成四章全文。逐章独立生成，每章写完后 LLM 自行统计字数、当场调整达标后再写下一章。首稿锚定建议字数中位数，减少偏离幅度。

1. Read `appendix_b.json`（完整五个顶层 key）
2. Read `references/writing_guide.md`
3. Read `seed_input`（从 T0 解析的路径）

4. 按以下顺序**逐章生成**，每章走"生成→自估字数→调整→复检"流程：

   **每章通用流程**：
   a. 生成该章初稿，Write 到 `_chN_draft.txt`
   b. LLM 自行统计该章中文字数（含中文标点），与目标范围对比
   c. 若低于下限则按差值扩充，若超出上限则按差值删减
   d. 调整后重新统计字数 → 达标后进入下一章

   **第一章 · 舆情概要**（B版 200-300字 / C版 400-600字）
   - **建议首稿**：B版约 250 字 / C版约 500 字
   - 基于 seed_input + LLM 对现实舆情事件的了解，概括写作
   - 禁止照搬 seed_input 原文。以具体日期、事件核心矛盾开篇
   - 末句以"当前，网络舆情主要聚焦……"收束。禁止任何模拟/推演表述

   **第二章 · 演化分析**（B版 450-650字 / C版 900-1300字）
   - **建议首稿**：B版约 550 字 / C版约 1100 字
   - 从 `evolution_analysis` 翻译为自然语言
   - 开头允许一句"以真实现实事件发展为基础，模拟推演显示……"
   - 禁止立场分、极化指数、群体数量、轮次编号、百分比等模拟指标

   **第三章 · 风险研判**（B版 400-600字 / C版 1000-1400字）
   - **建议首稿**：B版约 500 字 / C版约 1200 字
   - 从 `risk_assessment` 翻译为自然语言
   - 禁止"推演""模拟""world""跨组""一致显示""识别该风险"等仿真术语
   - 文风平实、流畅、专业——定性判断 + 现实传导链条 + 指向主体

   **第四章 · 对策意见**（B版 180-280字 / C版 1000-1400字）
   - **建议首稿**：B版约 230 字 / C版约 1200 字
   - 从 `countermeasures` 翻译，A+B+C 组织
   - B 版：确认风险 ≤3 条时全部实质性展开；>3 条时展开最核心 2-3 条，其余仅标等级。每条对策必须含具体措施，禁止一句话敷衍；C 版全部展开

5. 四章全部达标后，通读全文做**一次**文风统一润色：仅调整章节过渡衔接和用词一致性，**不改变各章字数**

**锚点 2**：正文中所有定性判断（风险等级、类型名称、主体名称、趋势方向）必须能在 `appendix_b.json` 中找到对应字段。正文禁止出现立场分、极化指数、群体数量、轮次编号、百分比等模拟指标。

### T4 — 审核 + 拼接 + 输出

1. Read `references/quality_checklist.yaml` + `references/appendix_a.md`
2. 对文字报告逐条跑审核清单（5 类审核项）
3. 致命/高严重度项自动修复一次；高严重度复审仍失败则视为致命，转入 _blocked
4. 审核结果判定：
   - **致命项全部通过** → 拼接输出两份文件：
     - **含附录版**：文字正文 + 附录 A（固定文本，从 `references/appendix_a.md` 直接拼入）+ 附录 B（`appendix_b.json` 原样拼入）
     - **无附录版**：仅文字正文，不含附录 A 和附录 B
   - **拼接方式**：使用 Write 工具写一个 Python 脚本 `assemble.py`，用 `json` 模块读取 `appendix_b.json` 完整数据，`json.dumps(data, ensure_ascii=False, indent=2)` 后拼入含附录版报告。附录 B 即 `appendix_b.json` 原样内容，无需额外转格式。**编码要求**：`assemble.py` 首行加 `# -*- coding: utf-8 -*-`，中文弯引号替换为直引号或括号（同 T2 步骤 6 的 ③④）。执行 `python3 assemble.py`（若 `python3` 不存在则 `python assemble.py`）后删除临时脚本。**禁止使用 `bash -c` 内联 Python**（会导致 `\n` 转义丢失）
   - **章节标题格式规范**：
     - 四章正文标题必须使用 `## 一、舆情概要` / `## 二、演化分析` / `## 三、风险研判` / `## 四、对策意见` 的 Markdown 二级标题语法
     - 章内子级标题必须遵循中文数字分级编号，按层级依次为：
       - 第一层（章标题）：`## 一、二、三、四`
       - 第二层（节标题）：`### （一）（二）（三）`——当章内存在多条并列内容（如多条风险、多条对策）时，每条必须使用此格式
       - 第三层：`1. 2. 3.`
       - 第四层：`（1）（2）（3）`
     - 编号必须从"（一）"开始连续递增，禁止使用字母序号（如 A/B/C）替代。C 版必须使用子级标题编号，B 版如有子标题也必须遵循此规范
   - 两份文件写入正式目录
   - **致命项未修复** → 禁止生成正式报告，输出到 `_blocked/<timestamp>/`（含 draft.md + audit_report.md + failure_reason.md）
5. **清理中间产物**：两份最终报告写入后，删除生成过程中遗留的临时文件，确保输出目录只保留阅读者需要的交付物：
   - 删除 `draft_body.md`（中间草稿，已拼入最终报告）
   - 删除逐章草稿文件（`_ch*_draft.txt` 等）
   - 删除生成过程中创建的临时脚本（`assemble.py`、`count_chars.py`、`_count*.py`、`concat_reports.py` 等）
   - **保留**：两份最终报告（含附录 + 无附录）、`appendix_b.json`（数据存档备查）、`_blocked/` 和 `debug_artifacts/`（如存在）
6. 调试留存：将 `appendix_b.json`、审核中间结果、脚本 stderr/stdout 写入 `debug_artifacts/<timestamp>/`。正式交付时可清理此目录，调试失败时作为复盘材料保留。

**锚点 3**：审核项 C3a（附录 B 内部一致性）、C3b（正文标签与附录 B 一致性）、C3c（正文公开数字与附录 B 一致性）逐项比对，末端兜底。

## 输出规范

**单一版本**（A 版、B 版或 C 版）：
```
./reports_output/
└── <safe_event_slug>/
    ├── <safe_event_slug>_舆情风险研判_<YYYYMMDD>_v<N>_含附录.md
    ├── <safe_event_slug>_舆情风险研判_<YYYYMMDD>_v<N>_无附录.md
    ├── _blocked/
    │   └── <timestamp>/
    │       ├── draft.md
    │       ├── audit_report.md
    │       └── failure_reason.md
    └── debug_artifacts/                 ← 调试复盘材料（可清理）
        └── <timestamp>/
            ├── appendix_b.json
            ├── audit_check_results.json
            └── script_output.log
```

**多版本**（A/B/C 任意多选，并发）：
```
./reports_output/
└── <safe_event_slug>/
    ├── appendix_b.json                  ← 共享数据报告（T1+T2 产出）
    ├── A版/
    │   ├── <safe_event_slug>_舆情风险研判_<YYYYMMDD>_v<N>_含附录.md
    │   └── <safe_event_slug>_舆情风险研判_<YYYYMMDD>_v<N>_无附录.md
    ├── B版/
    │   ├── <safe_event_slug>_舆情风险研判_<YYYYMMDD>_v<N>_含附录.md
    │   └── <safe_event_slug>_舆情风险研判_<YYYYMMDD>_v<N>_无附录.md
    ├── C版/
    │   ├── ……
    ├── _blocked/
    │   └── <timestamp>/
    │       ├── draft.md
    │       ├── audit_report.md
    │       └── failure_reason.md
    └── debug_artifacts/
        └── <timestamp>/
            ├── appendix_b.json
            ├── audit_check_results.json
            └── script_output.log
```

- 版本号 N：检查当天已有文件，取 `max(已有)+1`，无已有则从 v1 起
- `safe_event_slug`：LLM 根据事件名提炼的简短概括（如"OPPO母亲节文案争议"），原始事件名保留在报告标题和 `appendix_b.meta.event_name` 中

## 环境解耦

- 所有路径均使用相对引用：`references/`（相对 Skill 目录）、`./reports_output/`（相对用户工作目录）
- Skill 文件内不出现任何绝对路径、固定盘符
- 同事拷走 `adarian-report-agent/` 文件夹即可在任意项目中使用
