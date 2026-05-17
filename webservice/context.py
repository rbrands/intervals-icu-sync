from contextvars import ContextVar

athlete_id_var: ContextVar[str] = ContextVar("athlete_id", default="")
api_key_var: ContextVar[str] = ContextVar("api_key", default="")
