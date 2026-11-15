"""FastAPI routes for the isolated Planetary Computer integration."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from external_data import planetary_computer as service


router = APIRouter(
    prefix="/api/v1/external/planetary-computer",
    tags=["external-scientific-data"],
)


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, service.ExternalDataError):
        raise HTTPException(error.status_code, str(error)) from error
    if isinstance(error, ValueError):
        raise HTTPException(422, str(error)) from error
    raise error


@router.get("/collections")
def collections(
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=service.MAX_COLLECTIONS),
    page: int = Query(default=1, ge=1, le=service.MAX_COLLECTION_PAGES),
) -> dict:
    try:
        return service.list_collections(search=search, limit=limit, page=page)
    except (ValueError, service.ExternalDataError) as exc:
        _raise_http_error(exc)


@router.get("/collections/{collection_id}")
def collection_detail(collection_id: str) -> dict:
    try:
        result = service.get_collection(collection_id)
        if result is None:
            raise HTTPException(404, "STAC collection was not found.")
        return result
    except HTTPException:
        raise
    except (ValueError, service.ExternalDataError) as exc:
        _raise_http_error(exc)


@router.get("/search")
def search(
    collection_id: str,
    bbox: str,
    datetime: str | None = None,
    page: int = Query(default=1, ge=1, le=service.MAX_SEARCH_PAGES),
    limit: int = Query(default=10, ge=1, le=service.MAX_PAGE_SIZE),
) -> dict:
    try:
        return service.search_items(
            collection_id=collection_id,
            bbox=bbox,
            datetime_range=datetime,
            page=page,
            limit=limit,
        )
    except (ValueError, service.ExternalDataError) as exc:
        _raise_http_error(exc)


@router.get("/items/{collection_id}/{item_id}")
def item_detail(collection_id: str, item_id: str) -> dict:
    try:
        result = service.inspect_item(collection_id, item_id)
        if result is None:
            raise HTTPException(404, "STAC item was not found.")
        return result
    except HTTPException:
        raise
    except (ValueError, service.ExternalDataError) as exc:
        _raise_http_error(exc)


@router.get("/items/{collection_id}/{item_id}/assets/{asset_key}")
def asset_detail(collection_id: str, item_id: str, asset_key: str) -> dict:
    try:
        result = service.inspect_asset(collection_id, item_id, asset_key)
        if result is None:
            raise HTTPException(404, "STAC asset was not found.")
        return result
    except HTTPException:
        raise
    except (ValueError, service.ExternalDataError) as exc:
        _raise_http_error(exc)


@router.get("/items/{collection_id}/{item_id}/assets/{asset_key}/preview")
def asset_preview(collection_id: str, item_id: str, asset_key: str) -> Response:
    try:
        content = service.preview_asset(collection_id, item_id, asset_key)
    except (ValueError, service.ExternalDataError) as exc:
        _raise_http_error(exc)
    if content.content_type not in service.PREVIEW_MEDIA_TYPES:
        raise HTTPException(415, "Asset response is not a supported image format.")
    return Response(
        content.body,
        media_type=content.content_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "X-COSMOS-Retrieved-At": content.retrieved_at_utc,
            "Content-Disposition": f'inline; filename="{quote(content.filename, safe="")}"',
        },
    )


@router.get("/items/{collection_id}/{item_id}/assets/{asset_key}/download")
def asset_download(collection_id: str, item_id: str, asset_key: str) -> Response:
    try:
        content = service.download_asset(collection_id, item_id, asset_key)
    except (ValueError, service.ExternalDataError) as exc:
        _raise_http_error(exc)
    return Response(
        content.body,
        media_type=content.content_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "X-COSMOS-Retrieved-At": content.retrieved_at_utc,
            "Content-Disposition": f'attachment; filename="{quote(content.filename, safe="")}"',
        },
    )
