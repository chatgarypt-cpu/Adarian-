# Prompt Inventory - Adarian MVP

生成时间：2026-04-14
版本：v1.1.20
来源：src/phase1_entity_extraction.py, src/phase1/*, src/phase3_tick_simulation.py, src/phase3/*, src/phase4_report_agent.py, profiling/prompts.py

---

## Prompt Family Summary

| prompt_id | source_file | task_family | output_type | complexity | in_main_flow |
|-----------|-------------|-------------|-------------|-------------|--------------|
| P1-A | phase1_entity_extraction.py | phase1_analyzer | json | medium | true |
| P1-G | phase1_entity_extraction.py | phase1_generator | json | high | true |
| P1-V | phase1_entity_extraction.py | phase1_validator | json | medium | true |
| P1-F | phase1/entity_extractor.py | phase1_fact | json | medium | true (v1.1.14+) |
| P1-P | phase1/group_planner.py | phase1_group | json | high | true (v1.1.14+) |
| P1-W | phase1/persona_writer.py | phase1_persona | json | medium | true (v1.1.14+) |
| P3-E | phase3_tick_simulation.py | phase3_event_entity | json | medium | true |
| P3-A | phase3_tick_simulation.py | phase3_agent | json | high | true |
| P3-C | phase3/context_builder.py | phase3_context | json | low | true |
| P4-R | phase4_report_agent.py | phase4_report | markdown | high | true |
| PR-S | profiling/prompts.py | profiling_simple | json | low | true |
| PR-G | profiling/prompts.py | profiling_generator | json | high | true |
| PR-V | profiling/prompts.py | profiling_validator | json | medium | true |

---

## Prompt Detail Cards

---

### P1-A: Analyzer (Phase 1 Parameter Setting)

**Source**: `src/phase1_entity_extraction.py:36-79`
**Constants**: `ANALYZER_SYSTEM_PROMPT`, `ANALYZER_USER_PROMPT`
**Task Family**: phase1_analyzer
**Output Type**: json (event_scale, event_controversy, event_summary, event_type, reasoning)
**Complexity**: medium
**In Main Flow**: true
**Status**: Active

**L3 (Production)**: `ANALYZER_SYSTEM_PROMPT` + `ANALYZER_USER_PROMPT`

**Purpose**: Analyze seed text → set event_scale (0-1) and event_controversy (0-1)

**Schema Complexity**:
- 5 output fields
- 2 numeric (0.0-1.0 range)
- 3 string

**Layering Candidates**:
- L1: "分析这个事件，输出 event_scale 和 event_controversy (0.0-1.0)" → just numeric output
- L2: Full prompt minus reasoning field and event_type
- L3: Current production version

---

### P1-G: Generator (Phase 1 Entity Extraction + Opinion Spreaders)

**Source**: `src/phase1_entity_extraction.py:86-211`
**Constants**: `GENERATOR_SYSTEM_PROMPT`, `GENERATOR_USER_PROMPT`
**Task Family**: phase1_generator
**Output Type**: json (nested event_entities, opinion_spreaders, relations)
**Complexity**: high
**In Main Flow**: true (being replaced by P1-F/P1-P/P1-W in v1.1.14+)
**Status**: Legacy (v1.1.14+ replaced by decoupled flow)

**L3 (Production)**: `GENERATOR_SYSTEM_PROMPT` + `GENERATOR_USER_PROMPT`

**Purpose**: Extract event entities + generate opinion spreaders with full persona

**Schema Complexity**:
- 3 top-level arrays
- event_entities: 7 fields
- opinion_spreaders: 14 fields including nested typical_phrases array
- relations: 3 fields
- Constraints: ≤15 total entities, percentage sum=100, I/P distribution rules

**Layering Candidates**:
- L1: "从事件材料中提取参与方和评论群体" → just names and basic roles
- L2: Keep entity extraction, remove persona enrichment (persona_name, typical_phrases, etc.)
- L3: Full production with all constraints and persona fields

**Replacement Architecture (v1.1.14+)**:
- P1-F: Entity fact extraction only
- P1-P: Opinion spreader skeleton generation
- P1-W: Persona enrichment for each group

---

### P1-V: Validator (Phase 1 Format Checking)

**Source**: `src/phase1_entity_extraction.py:218-275`
**Constants**: `VALIDATOR_SYSTEM_PROMPT`, `VALIDATOR_USER_PROMPT`
**Task Family**: phase1_validator
**Output Type**: json (pass: bool, message: str, errors: array)
**Complexity**: medium
**In Main Flow**: true
**Status**: Active

**L3 (Production)**: `VALIDATOR_SYSTEM_PROMPT` + `VALIDATOR_USER_PROMPT`

**Purpose**: Validate Generator output format, return pass/fail with error list

**Schema Complexity**:
- 3 fields
- errors array length variable
- 18 validation rules in prompt

**Layering Candidates**:
- L1: "校验这个JSON格式是否正确" → basic JSON syntax check only
- L2: Core structural checks (field presence, type checking) without persona rules
- L3: Full 18-rule validation including persona constraints

---

### P1-F: Fact Extractor (Phase 1 v1.1.14+)

**Source**: `src/phase1/entity_extractor.py:17-91`
**Constants**: `FACT_EXTRACTOR_SYSTEM_PROMPT`, `FACT_EXTRACTOR_USER_PROMPT`
**Task Family**: phase1_fact
**Output Type**: json (event_entities, relations only - no opinion_spreaders)
**Complexity**: medium
**In Main Flow**: true (v1.1.14+)
**Status**: Active (replaces P1-G entity extraction portion)

**L3 (Production)**: `FACT_EXTRACTOR_SYSTEM_PROMPT` + `FACT_EXTRACTOR_USER_PROMPT`

**Purpose**: Extract event facts and relations only, no opinion spreader generation

**Schema Complexity**:
- 2 arrays: event_entities (7 fields), relations (3 fields)
- Clear exit condition: no opinion_spreaders field

**Layering Candidates**:
- L1: "提取事件参与方和关系" → simple entity extraction
- L2: Full fact prompt minus original_statement and can_speak rules
- L3: Current production with all extraction rules

---

### P1-P: Group Planner (Phase 1 v1.1.14+)

**Source**: `src/phase1/group_planner.py:16-83`
**Constants**: `GROUP_PLANNER_SYSTEM_PROMPT`, `GROUP_PLANNER_USER_PROMPT`
**Task Family**: phase1_group
**Output Type**: json (opinion_spreaders skeleton - no persona fields)
**Complexity**: high
**In Main Flow**: true (v1.1.14+)
**Status**: Active (replaces P1-G opinion spreader generation portion)

**L3 (Production)**: `GROUP_PLANNER_SYSTEM_PROMPT` + `GROUP_PLANNER_USER_PROMPT`

**Purpose**: Generate opinion spreader skeletons (group_name, description, I, susceptibility, raw_weight)

**Schema Complexity**:
- 1 array: opinion_spreaders
- 6 fields per spreader (NOT including persona fields)
- Constraints: I distribution based on event_scale, raw_weight > 0

**Layering Candidates**:
- L1: "为这个事件生成评论群体" → just group names
- L2: Keep I/susceptibility, remove distribution constraints
- L3: Full production with IPC framework and distribution rules

**Key Difference from P1-G**: P1-P does NOT output persona fields (persona_name, age_range, occupation, personality, motivation, typical_phrases, communication_style) - those are handled by P1-W

---

### P1-W: Persona Writer (Phase 1 v1.1.14+)

**Source**: `src/phase1/persona_writer.py:26-82`
**Constants**: `PERSONA_WRITER_SYSTEM_PROMPT`, `PERSONA_WRITER_USER_PROMPT`
**Task Family**: phase1_persona
**Output Type**: json (persona profile - 7 fields)
**Complexity**: medium
**In Main Flow**: true (v1.1.14+)
**Status**: Active

**L3 (Production)**: `PERSONA_WRITER_SYSTEM_PROMPT` + `PERSONA_WRITER_USER_PROMPT`

**Purpose**: Generate persona details for a group skeleton (persona_name, age_range, occupation, personality, motivation, typical_phrases, communication_style)

**Schema Complexity**:
- 7 fields per persona
- typical_phrases is array (2-3 items)
- persona_name must be Chinese name
- age_range must match XX-XX format

**Layering Candidates**:
- L1: "为这个群体起一个名字和简单描述" → just persona_name and description
- L2: Add personality and typical_phrases, remove age_range and occupation constraints
- L3: Full production with all persona fields and format constraints

---

### P3-E: Event Entity Post (Phase 3 Tick 0)

**Source**: `src/phase3_tick_simulation.py:91-122`
**Constant**: `EVENT_ENTITY_POST_SYSTEM_PROMPT`
**Task Family**: phase3_event_entity
**Output Type**: json (comment, reasoning)
**Complexity**: medium
**In Main Flow**: true
**Status**: Active

**L3 (Production)**: `EVENT_ENTITY_POST_SYSTEM_PROMPT` + hardcoded user prompt

**Purpose**: Event entity generates initial statement at Tick 0

**Schema Complexity**:
- 2 fields: comment (≤100 chars), reasoning (≤30 chars)
- Constraints: must represent entity's official stance, no apology/clarification statements

**Layering Candidates**:
- L1: "[entity_name] 说一句话代表你的立场" → unconstrained
- L2: Add JSON format constraint, remove role/background filling
- L3: Full production with identity framing and prohibition rules

---

### P3-A: Agent Post (Phase 3 Tick N)

**Source**: `src/phase3_tick_simulation.py:125-178`
**Constants**: `AGENT_POST_SYSTEM_PROMPT`, `AGENT_POST_USER_PROMPT`
**Task Family**: phase3_agent
**Output Type**: json (comment, new_stance, reasoning)
**Complexity**: high
**In Main Flow**: true
**Status**: Active

**L3 (Production)**: `AGENT_POST_SYSTEM_PROMPT` + `AGENT_POST_USER_PROMPT`

**Purpose**: Opinion spreader generates comment at Tick N, considering followed agents and history

**Schema Complexity**:
- 3 fields: comment (≤50 chars), new_stance (1.0-10.0), reasoning (≤30 chars)
- Dynamic context: event entity post + followed agents' comments + agent history
- Conditional prompts: stance_semantics, confirmation_bias_prompt, opinion_pressure_prompt

**Layering Candidates**:
- L1: "作为[群体名]说一句话" → minimal context
- L2: Add JSON format and stance range, remove confirmation bias and opinion pressure
- L3: Full production with all dynamic context and bias mechanisms

**Dynamic Elements**:
- {persona_name}, {group_name}, {age_range}, {occupation}, {personality}, {motivation}, {typical_phrases}
- {related_entity}, {communication_style}, {description}
- {stance_semantics} - injected from STANCE_SEMANTICS constant
- {confirmation_bias_prompt} - injected from CONFIRMATION_BIAS_PROMPTS dict
- {opinion_pressure_prompt} - conditional based on group_distribution_strategy

---

### P3-C: Context Builder (Phase 3 v1.1.18+ Lightweight)

**Source**: `src/phase3/context_builder.py:10-71`
**Function**: `build_lightweight_context()`
**Task Family**: phase3_context
**Output Type**: tuple (system_prompt, user_prompt) → json
**Complexity**: low
**In Main Flow**: true (v1.1.18+)
**Status**: Active

**L3 (Production)**: `build_lightweight_context()` function output

**Purpose**: Build lightweight context for agent post generation (v1.1.18+ replaces heavy persona档案 in context)

**Schema Complexity**:
- System prompt: identity + lightweight profile (6 fields) + JSON constraint
- User prompt: event summary + event entity post + followed comments + history
- Output: comment (≤50 chars), new_stance (1.0-10.0), reasoning (≤30 chars)

**Layering Candidates**:
- L1: Pure unframed "说一句话评论这个事件"
- L2: Add persona name and basic stance
- L3: Full lightweight context with followed agents and history

**与 P3-A 的关系**: `build_lightweight_context()` 输出的 prompt 字符串被 `SimulationEngine.generate_opinion_spreader_post()` 使用，替代了 `AGENT_POST_SYSTEM_PROMPT` 中的重 persona 档案

---

### P4-R: Report Agent (Phase 4)

**Source**: `src/phase4_report_agent.py:39-79`
**Constant**: `REPORT_SYSTEM_PROMPT`
**Task Family**: phase4_report
**Output Type**: markdown (500-800 lines, 10 sections)
**Complexity**: high
**In Main Flow**: true
**Status**: Active

**L3 (Production)**: `REPORT_SYSTEM_PROMPT` + structured data context

**Purpose**: Generate comprehensive public opinion analysis report from simulation results

**Schema Complexity**:
- 10 report sections with emoji headers
- Includes: event summary, entity map, Tick 0 posts, inflection points, evolution, stance changes, polarization, insights, risk assessment
- Output is freeform markdown with structural expectations

**Layering Candidates**:
- L1: "根据数据写一份报告" → unconstrained markdown
- L2: Keep section structure, remove emoji and formatting requirements
- L3: Full production with all 10 sections, emoji, and risk assessment rules

**Input Data**: build_full_report_context() produces structured input including event metrics, entity list, tick data, stance changes

---

## Phase 3 Source Map

### 模块拆分状态

| 模块 | 文件 | 性质 | Prompt 来源 |
|------|------|------|------------|
| speaker_selector | `src/phase3/speaker_selector.py` | 纯逻辑 | 无 LLM prompt |
| state_updater | `src/phase3/state_updater.py` | 纯逻辑 | 无 LLM prompt |
| simulation_card | `src/phase3/simulation_card.py` | 纯逻辑 | 无 LLM prompt |
| context_builder | `src/phase3/context_builder.py` | Prompt 生成函数 | ✅ P3-C 生成函数在此 |
| event_entity_post | `phase3_tick_simulation.py` | Prompt 常量 | ❌ P3-E 常量仍在主文件 |
| agent_post | `phase3_tick_simulation.py` | Prompt 常量 | ❌ P3-A 常量仍在主文件 |

**结论**：模块逻辑已拆分为独立文件，但 `EVENT_ENTITY_POST_SYSTEM_PROMPT` 和 `AGENT_POST_SYSTEM_PROMPT` 两个 prompt 常量仍留在 `phase3_tick_simulation.py` 主入口文件中。

### P3-A 与 P3-C 的关系

- **P3-C** (`build_lightweight_context()`)：生成"轻量版" agent post prompt
  - 在 v1.1.18+ 中使用，作为 P3-A 的上下文构建方式
  - 输出 system_prompt + user_prompt 字符串，供 `SimulationEngine.generate_opinion_spreader_post()` 调用

- **P3-E** (`EVENT_ENTITY_POST_SYSTEM_PROMPT`)：事件实体发言 prompt，独立常量在主文件

- **P3-A** (`AGENT_POST_SYSTEM_PROMPT` + `AGENT_POST_USER_PROMPT`)：意见传播者发言 prompt
  - v1.1.18+ 实际使用 `build_lightweight_context()` 输出的轻量版

---

### PR-S: Simple Profiling Prompt

**Source**: `profiling/prompts.py:13-23`
**Constants**: `SIMPLE_PROMPT_SYSTEM`, `SIMPLE_PROMPT_USER`
**Task Family**: profiling_simple
**Output Type**: json (summary: string, risk_level: string)
**Complexity**: low
**In Main Flow**: true (profiling only)
**Status**: Active

**L3 (Production)**: `SIMPLE_PROMPT_SYSTEM` + `SIMPLE_PROMPT_USER`

**Purpose**: Ultra-simple baseline for measuring model's basic JSON following capability

**Schema Complexity**:
- 2 fields: summary (≤50 chars), risk_level (enum: low/medium/high)
- Fixed seed text

**Layering Candidates**:
- L1: N/A - this IS the L1 (ultra-light baseline)
- L2: Add risk_level enum constraint
- L3: Current production with format framing

---

### PR-G: Profiling Generator (uses P1-G)

**Source**: `profiling/prompts.py:26-42`
**Function**: `build_generator_prompts()`
**Task Family**: profiling_generator
**Output Type**: json (same as P1-G)
**Complexity**: high
**In Main Flow**: true (profiling only)
**Status**: Active

**L3 (Production)**: `build_generator_prompts()` wraps P1-G with case data

**Purpose**: Profile Generator's entity extraction + opinion spreader generation capability

---

### PR-V: Profiling Validator (uses P1-V)

**Source**: `profiling/prompts.py:45-51`
**Function**: `build_validator_prompts()`
**Task Family**: profiling_validator
**Output Type**: json (same as P1-V)
**Complexity**: medium
**In Main Flow**: true (profiling only)
**Status**: Active

**L3 (Production)**: `build_validator_prompts()` wraps P1-V with seed and content

**Purpose**: Profile Validator's format checking capability

---

## Prompt Dependency Graph

```
Seed Text
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 1 (v1.1.14+ Decoupled)                                │
│                                                             │
│  ┌─────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ P1-A    │───▶│ P1-F         │───▶│ P1-P             │   │
│  │Analyzer │    │ Fact Extract │    │ Group Planner    │   │
│  └─────────┘    └──────────────┘    └────────┬─────────┘   │
│                                                │             │
│                                                ▼             │
│                                     ┌──────────────────┐    │
│                                     │ P1-W             │    │
│                                     │ Persona Writer   │    │
│                                     └────────┬─────────┘    │
│                                              │              │
│                                              ▼              │
│                                     ┌──────────────────┐    │
│                                     │ Rules Engine     │    │
│                                     │ (P derivation,    │    │
│                                     │  percentage norm) │    │
│                                     └────────┬─────────┘    │
└──────────────────────────────────────────────┼──────────────┘
                                               │
                                               ▼
                                    EntityExtractionOutput
                                               │
                    ┌──────────────────────────┴──────────────────────┐
                    │                                               │
                    ▼                                               ▼
┌─────────────────────────┐                        ┌─────────────────────────┐
│ Phase 2                 │                        │ Phase 3                 │
│ Topology Builder         │                        │                          │
│ (No LLM prompts)         │                        │  ┌──────────────────┐   │
└─────────────────────────┘                        │  │ P3-E             │   │
                    │                              │  │ Event Entity Post│   │
                    │                              │  └──────────────────┘   │
                    ▼                              │           │            │
        Phase2Output (Graph)                       │           ▼            │
                    │                              │  ┌──────────────────┐   │
                    │                              │  │ P3-A / P3-C      │   │
                    │                              │  │ Agent Post       │   │
                    │                              │  │ (Tick N)         │   │
                    │                              │  └──────────────────┘   │
                    │                              │           │            │
                    │                              │           ▼            │
                    │                              │  ┌──────────────────┐   │
                    │                              │  │ Silent Agent     │   │
                    │                              │  │ Update (no LLM)  │   │
                    │                              │  └──────────────────┘   │
                    │                              └─────────────────────────┘
                    │                                         │
                    ▼                                         ▼
            social_graph.json                          tick_logs/
                    │                                         │
                    │                                         ▼
                    │                              ┌─────────────────────────┐
                    │                              │ Phase 4                 │
                    │                              │                          │
                    │                              │  ┌──────────────────┐   │
                    │                              │  │ P4-R             │   │
                    │                              │  │ Report Agent     │   │
                    │                              │  └──────────────────┘   │
                    │                              └─────────────────────────┘
                    ▼                                         │
        final_report.json + final_report.md                      │
                                                               ▼
                                                     outputs/
```

---

## Historical Prompts (Not in Main Flow)

### P1-G-Legacy: Original Generator (v1.1.4 - v1.1.13)

**Source**: `src/phase1_entity_extraction.py:86-211` (still exists, replaced by P1-F/P1-P/P1-W)
**Status**: Legacy - kept for compatibility, main flow now uses decoupled P1-F → P1-P → P1-W

### STANCE_SEMANTICS

**Source**: `src/phase3_tick_simulation.py:48-56`
**Type**: Constants embedded in prompt strings
**Purpose**: Define stance_score semantics (1.0-3.0 criticism, 4.0-6.0 neutral, 7.0-10.0 support)

### CONFIRMATION_BIAS_PROMPTS

**Source**: `src/phase3_tick_simulation.py:59-81`
**Type**: Dictionary of prompt fragments
**Purpose**: Inject confirmation bias behavior (strong/weak/none)
