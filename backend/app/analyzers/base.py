from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.schemas.finding import SeverityEnum, ConfidenceEnum, CategoryEnum, VerificationStatusEnum


@dataclass
class NormalizedFinding:
    rule_id: str
    source_analyzer: str
    file_path: str
    start_line: int
    end_line: Optional[int]
    severity: SeverityEnum
    confidence: ConfidenceEnum
    category: CategoryEnum
    title: str
    explanation: str
    evidence: Optional[str] = None
    remediation: Optional[str] = None
    doc_url: Optional[str] = None
    is_ai_suggested: bool = False
    is_demo: bool = False
    verification_status: VerificationStatusEnum = VerificationStatusEnum.UNREVIEWED


@dataclass
class AnalyzerResult:
    analyzer_name: str
    status: str  # "SUCCESS", "FAILED", "SKIPPED"
    duration_seconds: float = 0.0
    findings: List[NormalizedFinding] = field(default_factory=list)
    message: Optional[str] = None
    skip_reason: Optional[str] = None


class BaseAnalyzer(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the analyzer."""
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """List of supported languages (e.g. ['Python'], ['JavaScript', 'TypeScript'])."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if required tools/dependencies for this analyzer are installed."""
        pass

    @abstractmethod
    async def analyze(
        self,
        project_dir: Path,
        manifest_items: List[Dict[str, Any]],
        detected_languages: List[str]
    ) -> AnalyzerResult:
        """Executes analysis and returns normalized findings."""
        pass
