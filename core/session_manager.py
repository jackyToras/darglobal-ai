import time
import uuid
from typing import Dict, List, Any, Optional

class TenantContext:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.created_at: float = time.time()
        self.last_active: float = time.time()
        self.history: List[Dict[str, Any]] = []
        self.isolated_chunks: List[Dict[str, Any]] = []

    def touch(self):
        self.last_active = time.time()

    def add_message(self, role: str, content: str):
        self.touch()
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def add_chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        self.touch()
        self.isolated_chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "text": text,
            "metadata": metadata or {},
            "timestamp": time.time()
        })

    def get_chunks(self) -> List[Dict[str, Any]]:
        self.touch()
        return list(self.isolated_chunks)

    def get_recent_messages(self, limit: int = 6) -> List[Dict[str, str]]:
        self.touch()
        return [{"role": m["role"], "content": m["content"]} for m in self.history[-limit:]]

class MultiTenantSessionManager:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl_seconds: int = ttl_seconds
        self._tenants: Dict[str, TenantContext] = {}

    def _cleanup_expired(self):
        now = time.time()
        expired = [sid for sid, ctx in self._tenants.items() if now - ctx.last_active > self.ttl_seconds]
        for sid in expired:
            del self._tenants[sid]

    def get_session(self, session_id: Optional[str] = None) -> TenantContext:
        self._cleanup_expired()
        if not session_id or not isinstance(session_id, str) or len(session_id.strip()) == 0:
            session_id = str(uuid.uuid4())
        session_id = session_id.strip()
        if session_id not in self._tenants:
            self._tenants[session_id] = TenantContext(session_id)
        return self._tenants[session_id]

    def get_user_chunks_only(self, session_id: str) -> List[Dict[str, Any]]:
        if session_id in self._tenants:
            return self._tenants[session_id].get_chunks()
        return []

    def clear_session(self, session_id: str) -> bool:
        if session_id in self._tenants:
            del self._tenants[session_id]
            return True
        return False

    def active_tenant_count(self) -> int:
        self._cleanup_expired()
        return len(self._tenants)

session_manager = MultiTenantSessionManager()
