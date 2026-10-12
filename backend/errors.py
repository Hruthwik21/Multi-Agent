"""Error taxonomy — frozen exception hierarchy (Phase 1)."""


class PolyMindError(Exception):
    """Base for all PolyMind errors."""


class LLMError(PolyMindError):
    pass


class LLMTimeout(LLMError):
    pass


class ToolError(PolyMindError):
    pass


class IngestionError(PolyMindError):
    pass


class VerificationError(PolyMindError):
    pass


class StorageError(PolyMindError):
    pass
