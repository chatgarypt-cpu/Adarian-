"""Legacy Phase 1 shim.

The implementation lives in `src.phase1.extraction`; prompt constants live in
`src.phase1.prompts`. This module keeps old imports working for profiling,
probes, and tests.
"""

from src.phase1.extraction import *  # noqa: F401,F403
from src.phase1.extraction import (  # noqa: F401
    _normalize_inner_cjk_quotes,
    _parse_json_candidate,
)
from src.phase1.prompts import (  # noqa: F401
    ANALYZER_SYSTEM_PROMPT,
    ANALYZER_USER_PROMPT,
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_PROMPT,
    VALIDATOR_SYSTEM_PROMPT,
    VALIDATOR_USER_PROMPT,
)
