"""Typed error hierarchy for PARALLAX.

The pipeline must distinguish failures it should retry, failures it should give
up on, and failures that are local to one stage but should not abort the whole
analysis. A blanket ``except Exception`` cannot make that decision; these types
can. Raise the specific type at each boundary (DB/LLM/parser/dynamic) and let
the worker layer decide retry-vs-fail-vs-continue from the type.

    ParallaxError
      |- TransientError      retry (with backoff)
      |    |- InfraError     postgres / redis / minio / neo4j / qdrant down
      |    |- LLMError       model provider 5xx, timeout, connection reset
      |- PermanentError      mark failed, do not retry
      |    |- DataError      malformed APK / unparseable input
      |    |- LLMBadOutputError   model returned garbage after retries
      |- StageError          this stage failed; continue the pipeline degraded
"""

from __future__ import annotations


class ParallaxError(Exception):
    """Base class for every error PARALLAX raises deliberately."""


class TransientError(ParallaxError):
    """A failure that is expected to clear on retry."""


class PermanentError(ParallaxError):
    """A failure that will not clear on retry; mark the analysis failed."""


class StageError(ParallaxError):
    """One pipeline stage failed, but the analysis can continue degraded.

    For example, the dynamic stage could not instrument the sample: the cortex
    still runs on static evidence and the report is marked static-only.
    """


class InfraError(TransientError):
    """A backing service (Postgres, Redis, MinIO, Neo4j, Qdrant) is unreachable."""


class LLMError(TransientError):
    """An LLM provider failed transiently (5xx, timeout, connection reset)."""


class DataError(PermanentError):
    """Input is malformed and cannot be analysed (bad APK, corrupt upload)."""


class LLMBadOutputError(PermanentError):
    """An LLM returned output that could not be parsed after retries."""


def is_retryable(exc: BaseException) -> bool:
    """True if the worker layer should retry on this exception."""
    return isinstance(exc, TransientError)
