"""python-substack's Api plus the listing endpoint that works today.

`Api.get_drafts` calls `/drafts`, which Substack now answers with
400 "Invalid value" (seen 2026-11-27, python-substack 0.10.0). The dashboard's
own `/post_management/{drafts,scheduled,published}` endpoints work and page
with offset/limit.
"""

from __future__ import annotations

from substack import Api

ORDER_BY = {"drafts": "draft_updated_at", "scheduled": "trigger_at", "published": "post_date"}


class Client(Api):
    def post_management(self, kind: str, offset: int, limit: int) -> dict:
        response = self._session.get(
            f"{self.publication_url}/post_management/{kind}",
            params={
                "offset": offset,
                "limit": limit,
                "order_by": ORDER_BY[kind],
                "order_direction": "desc",
            },
        )
        return Api._handle_response(response=response)
