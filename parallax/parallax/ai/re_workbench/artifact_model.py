from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class YaraMatch(BaseModel):
    rule: str
    namespace: str
    tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    strings: List[Dict[str, Any]] = Field(default_factory=list)


class StaticAnalysisFeatures(BaseModel):
    package_name: str
    app_name: str
    version_name: str
    version_code: str
    min_sdk: str
    target_sdk: str
    main_activity: Optional[str]
    permissions: List[str] = Field(default_factory=list)
    activities: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    receivers: List[str] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=list)
    is_valid: bool


class REArtifactModel(BaseModel):
    """
    Unified Artifact Model representing the RE Workbench state for a given APK.
    Aggregates Androguard static features, Jadx decompilation metadata, and YARA matches.
    """

    sha256: str
    static_features: StaticAnalysisFeatures
    yara_matches: List[YaraMatch] = Field(default_factory=list)
    jadx_output_dir: Optional[str] = None
    decompiled_s3_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
