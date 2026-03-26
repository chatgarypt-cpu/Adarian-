"""
全局配置文件
---
包含 API 配置、模型参数、路径配置等全局设置。
Why: 集中管理配置便于修改，避免硬编码。
"""

from pathlib import Path
from dotenv import load_dotenv
import os

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

# 社交网络拓扑输出路径
SOCIAL_GRAPH_PATH = OUTPUTS_DIR / "social_graph.json"

# 每轮交互日志目录
TICK_LOGS_DIR = OUTPUTS_DIR / "tick_logs"

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

# 默认模型名称
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek-chat")

# DeepSeek 模型
DEEPSEEK_MODEL = "deepseek-chat"

# Zhipu 模型
ZHIPU_MODEL = "glm-4"

# Qwen 模型
QWEN_MODEL = "qwen-turbo"

# =============================================================================
# LLM 调用参数
# =============================================================================

# Temperature 参数 (控制创造性，0=确定性强，1=创造性强)
DEFAULT_TEMPERATURE = 0.7

# 最大 Token 数
DEFAULT_MAX_TOKENS = 2048

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
MAX_TICKS = 10

# 收敛阈值 (当极化指数变化小于此值时停止)
CONVERGENCE_THRESHOLD = 0.05

# 每个 Agent 每轮最多读取的发言数
MAX_POSTS_PER_TICK = 5

# =============================================================================
# Phase 4 参数: 报告生成
# =============================================================================

# 报告生成使用的历史 tick 数
REPORT_LOOKBACK_TICKS = 5

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

def get_model_name() -> str:
    """根据 provider 返回对应的模型名称"""
    if LLM_PROVIDER == "deepseek":
        return DEEPSEEK_MODEL
    elif LLM_PROVIDER == "zhipu":
        return ZHIPU_MODEL
    elif LLM_PROVIDER == "qwen":
        return QWEN_MODEL
    else:
        return DEFAULT_MODEL


def ensure_dirs():
    """确保所有必要目录存在"""
    for dir_path in [SEEDS_DIR, OUTPUTS_DIR, TICK_LOGS_DIR, CHROMADB_PATH]:
        dir_path.mkdir(parents=True, exist_ok=True)
