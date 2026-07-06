"""Search MinIO takes/ prefix."""

from __future__ import annotations

import os

from contentos_sources.domain.source_candidate import SourceAsset, SourceCandidate, SourceHealth
from contentos_sources.domain.source_query import SourceQuery


class LocalLibrarySource:
    source_id = "local_library"

    async def search(self, query: SourceQuery) -> list[SourceCandidate]:
        from minio import Minio

        client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "contentos"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "contentos_secret"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )
        bucket = os.getenv("MINIO_BUCKET", "contentos")
        prefix = "takes/"
        terms = _terms(query)
        candidates: list[SourceCandidate] = []
        for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
            name = obj.object_name or ""
            if not name.endswith((".mp4", ".mov", ".webm")):
                continue
            label = name.split("/")[-1]
            if terms and not any(t in name.lower() for t in terms):
                continue
            score = _score(name, terms)
            candidates.append(
                SourceCandidate(
                    source_id=self.source_id,
                    candidate_id=name,
                    title=label,
                    score=score,
                    reason="MinIO take library match",
                    metadata={"bucket": bucket, "key": name},
                )
            )
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:10]

    async def fetch(self, candidate_id: str) -> SourceAsset:
        from minio import Minio

        client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "contentos"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "contentos_secret"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )
        bucket = os.getenv("MINIO_BUCKET", "contentos")
        import hashlib

        response = client.get_object(bucket, candidate_id)
        data = response.read()
        response.close()
        response.release_conn()
        sha = hashlib.sha256(data).hexdigest()
        return SourceAsset(
            source_id=self.source_id,
            candidate_id=candidate_id,
            data=data,
            filename=candidate_id.split("/")[-1],
            metadata={"bucket": bucket, "key": candidate_id},
            sha256=sha,
        )

    async def health(self) -> SourceHealth:
        try:
            from minio import Minio

            client = Minio(
                os.getenv("MINIO_ENDPOINT", "minio:9000"),
                access_key=os.getenv("MINIO_ACCESS_KEY", "contentos"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "contentos_secret"),
                secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            )
            client.bucket_exists(os.getenv("MINIO_BUCKET", "contentos"))
            return SourceHealth(self.source_id, True, "MinIO reachable")
        except Exception as exc:
            return SourceHealth(self.source_id, False, str(exc))


def _terms(query: SourceQuery) -> list[str]:
    parts = [query.scene_description, query.visual_hint, query.topic, query.scene_label, *query.tags]
    terms: list[str] = []
    for p in parts:
        for word in p.lower().replace("_", " ").split():
            if len(word) > 2:
                terms.append(word)
    return terms


def _score(name: str, terms: list[str]) -> float:
    if not terms:
        return 0.5
    lower = name.lower()
    hits = sum(1 for t in terms if t in lower)
    return min(1.0, hits / max(len(terms), 1))
