"""Template extraction: Drain3 when available, regex masking as a documented fallback.

Drain3 learns templates incrementally, so early messages may get a template that later becomes
more general. The log processor therefore runs two passes: `learn()` over the whole file, then
`extract()` over every message so all rows get the converged template.
"""

import hashlib
import logging
from typing import NamedTuple, Protocol

from app.parsers.regex_parser import MASK_PATTERNS, extract_parameters, mask_message

logger = logging.getLogger(__name__)


class TemplateResult(NamedTuple):
    template_text: str
    template_hash: str
    parameters: list[str]


def template_hash(template_text: str) -> str:
    return hashlib.sha1(template_text.encode("utf-8")).hexdigest()[:12]  # noqa: S324 (not security)


class TemplateExtractor(Protocol):
    name: str
    errors: int

    def learn(self, message: str) -> None: ...

    def extract(self, message: str) -> TemplateResult: ...


class RegexTemplateExtractor:
    """Stateless masking-based templates. Also the fallback for Drain3 failures."""

    def __init__(self, name: str = "regex", fallback_reason: str | None = None) -> None:
        self.name = name
        self.errors = 0
        self.fallback_reason = fallback_reason

    def learn(self, message: str) -> None:
        return None

    def extract(self, message: str) -> TemplateResult:
        template = mask_message(" ".join(message.split())) or "<empty>"
        return TemplateResult(template, template_hash(template), extract_parameters(template, message))


class DrainTemplateExtractor:
    name = "drain3"

    def __init__(self, sim_th: float = 0.4, depth: int = 4, max_clusters: int | None = 5000) -> None:
        from drain3 import TemplateMiner  # ImportError is handled by create_extractor
        from drain3.masking import MaskingInstruction
        from drain3.template_miner_config import TemplateMinerConfig

        config = TemplateMinerConfig()
        config.drain_sim_th = sim_th
        config.drain_depth = depth
        config.drain_max_clusters = max_clusters
        config.profiling_enabled = False
        config.masking_instructions = [MaskingInstruction(p, "*") for p in MASK_PATTERNS]
        self._miner = TemplateMiner(persistence_handler=None, config=config)
        self._fallback = RegexTemplateExtractor()
        self.errors = 0

    def learn(self, message: str) -> None:
        try:
            self._miner.add_log_message(" ".join(message.split()))
        except Exception:
            self.errors += 1
            logger.exception("Drain3 failed while learning a message")

    def extract(self, message: str) -> TemplateResult:
        try:
            result = self._miner.add_log_message(" ".join(message.split()))
            template = result["template_mined"]
            return TemplateResult(template, template_hash(template), extract_parameters(template, message))
        except Exception:
            self.errors += 1
            logger.exception("Drain3 failed while extracting a template; using regex fallback")
            return self._fallback.extract(message)


def create_extractor(kind: str = "drain") -> TemplateExtractor:
    """Build the requested extractor; silently-but-recorded fallback to regex if Drain3 is missing."""
    if kind == "drain":
        try:
            return DrainTemplateExtractor()
        except ImportError:
            logger.warning("drain3 is not installed; using the regex template fallback")
            return RegexTemplateExtractor(name="regex-fallback", fallback_reason="drain3 not installed")
    return RegexTemplateExtractor()
