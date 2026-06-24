"""
Phase 1: 实体提取与分类模块 — 向后兼容导入层。

此文件仅做 re-export，所有实际实现在：
  - utils.py       (JSON 解析工具)
  - analyzer.py    (种子材料分析)
  - generator.py   (实体生成 + 并发传播者)
  - compiler.py    (后处理 + 归一化)
  - orchestrator.py (编排 + Repair Loop)
"""
from adarian.schemas import EntityExtractionOutput as EntityExtractionOutput

from .utils import (
    _normalize_inner_cjk_quotes,
    _normalize_unescaped_quotes_inside_string_values,
    _parse_json_candidate,
    _parse_llm_json_payload,
    _coerce_top_level_object,
)
from .analyzer import analyzer_set_parameters
from .generator import (
    generator_create_event_entities,
    generator_create_spreader,
    generator_create_spreaders_concurrent,
)
from .compiler import _post_process_entities
from .orchestrator import (
    MAX_RETRIES,
    extract_entities,
    extract_entities_from_file,
    extract_entities_with_validation,
    save_entities_output,
)
