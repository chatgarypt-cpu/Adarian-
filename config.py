"""
全局配置文件
---
包含 API 配置、模型参数、路径配置等全局设置。
Why: 集中管理配置便于修改，避免硬编码。
"""

import sys
import os

# Windows 环境下设置 UTF-8 编码
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# =============================================================================
# 项目路径配置
# =============================================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 源代码目录
SRC_DIR = PROJECT_ROOT / "src"

# 种子材料目录
SEEDS_DIR = PROJECT_ROOT / "seeds"

# 输出目录
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Agent 画像输出路径
AGENTS_PROFILE_PATH = OUTPUTS_DIR / "agents_profile.json"

# Phase 1 实体提取输出路径
ENTITIES_OUTPUT_PATH = OUTPUTS_DIR / "entities_and_relations.json"

# 社交网络拓扑输出路径
SOCIAL_GRAPH_PATH = OUTPUTS_DIR / "social_graph.json"

# 每轮交互日志目录
TICK_LOGS_DIR = OUTPUTS_DIR / "tick_logs"

# Phase 3 日志聚合输出路径
TICK_LOGS_PATH = OUTPUTS_DIR / "tick_logs.json"

# 最终报告输出路径
FINAL_REPORT_PATH = OUTPUTS_DIR / "final_report.md"

# ChromaDB 本地存储路径
CHROMADB_PATH = PROJECT_ROOT / ".chromadb"

# =============================================================================
# LLM API 配置
# =============================================================================

# API Provider 选择: "openai", "deepseek", "zhipu", "qwen"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")

# API Key (从环境变量读取)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# 基础 URL (用于兼容不同 provider)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")

# =============================================================================
# LLM Fallback 配置（内网不通时自动切换外网模型）
# =============================================================================

FALLBACK_ENABLED = os.getenv("FALLBACK_ENABLED", "true").lower() == "true"
FALLBACK_PROVIDER = os.getenv("FALLBACK_PROVIDER", "deepseek")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "deepseek-chat")
FALLBACK_BASE_URL = os.getenv("FALLBACK_BASE_URL", "https://api.deepseek.com/v1")
FALLBACK_API_KEY = os.getenv("FALLBACK_API_KEY") or os.getenv("LLM_API_KEY", "")

# =============================================================================
# 模型名称
# =============================================================================

# DeepSeek 模型
DEEPSEEK_MODEL = "deepseek-chat"

# Zhipu 模型
ZHIPU_MODEL = "glm-4"

# Qwen 模型
QWEN_MODEL = os.getenv("QWEN_MODEL") or ""

# 默认模型（非 qwen/deepseek/zhipu 时的兜底）
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")

# =============================================================================
# LLM 调用参数
# =============================================================================

# Temperature 参数 (控制创造性，0=确定性强，1=创造性强)
DEFAULT_TEMPERATURE = 0.7

# 最大 Token 数
DEFAULT_MAX_TOKENS = 8192

# 重试次数
LLM_RETRY_TIMES = 3

# 重试间隔 (秒)
LLM_RETRY_DELAY = 1

# =============================================================================
# Phase 1 参数: 动态人群生成
# =============================================================================

# Agent 数量约束
MAX_AGENTS = 15
MIN_AGENTS = 5

# Archetype 数量约束
MIN_ARCHETYPES = 3
MAX_ARCHETYPES = 8

# =============================================================================
# Phase 2 参数: 社交拓扑构建
# =============================================================================

# 每个核心节点最少粉丝数
MIN_FOLLOWERS_PER_CORE = 1

# 核心节点占比 (core 节点占总 Agent 的比例)
CORE_NODE_RATIO = 0.2

# =============================================================================
# Phase 3 参数: 模拟推演
# =============================================================================

# 最大模拟轮数
MAX_TICKS = 5

# Phase 1 传播者并发生成最大并发数（默认 N = 无人工上限）
# 实际并发由二分降级自动控制：N → N/2 → ... → 1
PHASE1_MAX_CONCURRENT_SPREADERS = 0

# Phase 3 tick 并发调度最大并发数（默认 N = 无人工上限）
# 实际并发由二分降级自动控制：N → N/2 → ... → 1
PHASE3_TICK_MAX_CONCURRENT_WORKERS = 0

# 收敛阈值 (当极化指数变化小于此值时停止)
CONVERGENCE_THRESHOLD = 0.05

# 每个 Agent 每轮最多读取的发言数
MAX_POSTS_PER_TICK = 3

# susceptibility 调制系数（v1.1.9 新增）
# 高 susceptibility（>0.7）的 agent 变化幅度可增加 50%
SUSCEPTIBILITY_MODULATION_FACTOR = 0.5

# =============================================================================
# Phase 4 参数: 报告生成
# =============================================================================

# 报告生成使用的历史 tick 数
REPORT_LOOKBACK_TICKS = 10

# =============================================================================
# ChromaDB 配置
# =============================================================================

# Collection 名称
CHROMA_COLLECTION_NAME = "adarian_memory"

# ChromaDB 是否持久化存储
CHROMA_PERSISTENT = True

# =============================================================================
# 工具函数
# =============================================================================

def get_model_name(task_type: str = "default") -> str:
    """根据 provider 返回对应的模型名称"""
    if LLM_PROVIDER == "deepseek":
        return DEEPSEEK_MODEL
    elif LLM_PROVIDER == "zhipu":
        return ZHIPU_MODEL
    elif LLM_PROVIDER == "qwen":
        if QWEN_MODEL:
            return QWEN_MODEL
        # .env 未显式指定时走 router
        from src.model_router import select as _select_model
        return _select_model(task_type)
    else:
        return DEFAULT_MODEL


def ensure_dirs():
    """确保所有必要目录存在"""
    for dir_path in [SEEDS_DIR, OUTPUTS_DIR, TICK_LOGS_DIR, CHROMADB_PATH]:
        dir_path.mkdir(parents=True, exist_ok=True)
