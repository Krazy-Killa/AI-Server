"""Admin release-bundle verification routes (verify and stage only; no apply)."""

import shutil
from threading import Lock

from fastapi import APIRouter

import release_bundle
from api import runtime

router = APIRouter()
_upload_lock = Lock()


def _limits() -> dict:
    return {
        "max_bytes": runtime.settings.update_max_bytes,
        "expiry_hours": runtime.settings.update_expiry_hours,
    }


def _require_enabled() -> None:
    if not runtime.settings.update_public_keys:
        raise runtime.HTTPException(
            status_code=503,
            detail="Release verification is not configured. "
            "Set AI_SERVER_UPDATE_PUBLIC_KEYS on the server.",
        )


@router.get("/api/admin/updates")
async def list_updates():
    settings = runtime.settings
    staged = await runtime.asyncio.to_thread(
        release_bundle.list_staged, settings.update_staging_dir
    )
    return {
        "enabled": bool(settings.update_public_keys),
        "apply_supported": False,
        "staged": staged,
        "limits": _limits(),
    }


@router.get("/api/admin/updates/{release_id}")
async def get_update(release_id: str):
    record = await runtime.asyncio.to_thread(
        release_bundle.get_staged, runtime.settings.update_staging_dir, release_id
    )
    if record is None:
        raise runtime.HTTPException(status_code=404, detail="Staged release not found.")
    return record


@router.delete("/api/admin/updates/{release_id}")
async def discard_update(release_id: str):
    removed = await runtime.asyncio.to_thread(
        release_bundle.discard_staged, runtime.settings.update_staging_dir, release_id
    )
    if not removed:
        raise runtime.HTTPException(status_code=404, detail="Staged release not found.")
    runtime.logger.info("Staged release %s discarded", release_id)
    return {"discarded": release_id}


@router.post("/api/admin/updates", status_code=201)
async def upload_update(request: runtime.Request):
    settings = runtime.settings
    _require_enabled()
    declared = request.headers.get("content-length", "")
    if declared:
        if not declared.isdigit() or int(declared) < 1:
            raise runtime.HTTPException(status_code=400, detail="Invalid Content-Length.")
        if int(declared) > settings.update_max_bytes:
            raise runtime.HTTPException(status_code=413, detail="Release bundle is too large.")
    if not _upload_lock.acquire(blocking=False):
        raise runtime.HTTPException(status_code=409, detail="Another upload is in progress.")
    upload_path = None
    try:
        staging = settings.update_staging_dir
        upload_path = await runtime.asyncio.to_thread(
            release_bundle.new_incoming_path, staging
        )
        expected = int(declared) if declared else settings.update_max_bytes
        free = await runtime.asyncio.to_thread(lambda: shutil.disk_usage(staging).free)
        if free < expected * 3:
            raise runtime.HTTPException(status_code=507, detail="Not enough free disk space to stage a release.")
        received = 0
        handle = await runtime.asyncio.to_thread(open, upload_path, "wb")
        try:
            async for chunk in request.stream():
                received += len(chunk)
                if received > settings.update_max_bytes:
                    raise runtime.HTTPException(
                        status_code=413, detail="Release bundle is too large."
                    )
                await runtime.asyncio.to_thread(handle.write, chunk)
        finally:
            await runtime.asyncio.to_thread(handle.close)
        if received == 0:
            raise runtime.HTTPException(status_code=400, detail="Upload body is empty.")
        try:
            record = await runtime.asyncio.to_thread(
                lambda: release_bundle.verify_and_stage(
                    upload_path,
                    staging_dir=staging,
                    trusted_keys=settings.update_public_keys,
                    expiry_seconds=settings.update_expiry_hours * 3600,
                )
            )
        except release_bundle.BundleConflict as error:
            raise runtime.HTTPException(status_code=409, detail=str(error)) from error
        except release_bundle.BundleError as error:
            runtime.logger.warning("Release bundle rejected: %s", error)
            raise runtime.HTTPException(status_code=422, detail=str(error)) from error
        runtime.logger.info(
            "Release %s (%s) verified and staged; signer %s",
            record["release_id"], record["version"], record["signer"],
        )
        return record
    finally:
        if upload_path is not None:
            await runtime.asyncio.to_thread(upload_path.unlink, True)
        _upload_lock.release()
