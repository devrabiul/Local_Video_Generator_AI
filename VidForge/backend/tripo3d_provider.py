"""Tripo3D API Provider and Base Image-to-3D Provider Interface.

Provides modular image-to-3D mesh generation and automatic humanoid rigging
for persistent character creation.
"""
from abc import ABC, abstractmethod
import os
import json
import asyncio
from pathlib import Path
from loguru import logger
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent

def get_tripo3d_api_key() -> str:
    """Retrieves Tripo3D API key from config files or environment variable."""
    # 1. Environment variable
    key = os.environ.get("TRIPO3D_API_KEY", "").strip()
    if key:
        return key

    # 2. VidForge/backend/config.json
    for cfg_path in [
        BASE_DIR / "backend" / "config.json",
        BASE_DIR / "config.json"
    ]:
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                val = str(data.get("tripo3d_api_key", "")).strip()
                if val:
                    return val
            except Exception:
                pass
    return ""


class BaseImageTo3DProvider(ABC):
    """Abstract provider interface for Image-to-3D and Rigging generation."""

    @abstractmethod
    async def generate_mesh(self, image_path: Path, prompt: str = "") -> dict:
        """Submits an image to generate a textured 3D mesh."""
        pass

    @abstractmethod
    async def poll_task(self, task_id: str) -> dict:
        """Polls the status of an active generation/rigging task."""
        pass

    @abstractmethod
    async def rig_model(self, model_id_or_path: str) -> dict:
        """Applies humanoid skeleton rigging to a 3D model."""
        pass

    @abstractmethod
    async def download_asset(self, url: str, output_path: Path) -> Path:
        """Downloads generated asset file to disk."""
        pass


class Tripo3DProvider(BaseImageTo3DProvider):
    """Tripo3D OpenAPI v2 implementation for Image-to-3D and humanoid auto-rigging."""

    BASE_URL = "https://api.tripo3d.ai/v2/openapi"

    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or get_tripo3d_api_key()).strip()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        if not self.api_key:
            raise ValueError(
                "Tripo3D API key is not configured. Please provide 'tripo3d_api_key' in config.json "
                "or export TRIPO3D_API_KEY in your environment."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def upload_image(self, image_path: Path) -> str:
        """Uploads a local image file to Tripo3D and returns the image token/URL."""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found at {image_path}")

        upload_url = f"{self.BASE_URL}/upload"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(image_path, "rb") as f:
                files = {"file": (image_path.name, f, "image/png")}
                res = await client.post(upload_url, headers=headers, files=files)
                if res.status_code != 200:
                    raise RuntimeError(f"Tripo3D image upload failed ({res.status_code}): {res.text}")
                data = res.json()
                image_token = data.get("data", {}).get("image_token") or data.get("image_token")
                if not image_token:
                    raise RuntimeError(f"Tripo3D did not return an image token: {data}")
                return image_token

    async def generate_mesh(self, image_path: Path, prompt: str = "") -> dict:
        """Submits an Image-to-3D task using Tripo3D."""
        self._headers() # Validate key
        image_token = await self.upload_image(image_path)

        payload = {
            "type": "image_to_model",
            "file": {
                "type": "png",
                "file_token": image_token
            }
        }
        if prompt:
            payload["prompt"] = prompt

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(f"{self.BASE_URL}/task", headers=self._headers(), json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Tripo3D generate task failed ({res.status_code}): {res.text}")
            data = res.json()
            task_id = data.get("data", {}).get("task_id") or data.get("task_id")
            return {
                "provider": "tripo3d",
                "task_id": task_id,
                "status": "QUEUED",
                "raw": data
            }

    async def poll_task(self, task_id: str) -> dict:
        """Polls task status on Tripo3D."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(f"{self.BASE_URL}/task/{task_id}", headers=self._headers())
            if res.status_code != 200:
                raise RuntimeError(f"Tripo3D status check failed ({res.status_code}): {res.text}")
            
            data = res.json()
            task_data = data.get("data", {})
            status = str(task_data.get("status", "")).upper() # PENDING, RUNNING, SUCCESS, FAILED
            progress = int(task_data.get("progress", 0))

            output = task_data.get("output", {})
            model_url = (
                output.get("pbr_model") or
                output.get("model") or
                output.get("rendered_image") or
                ""
            )

            return {
                "provider": "tripo3d",
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "model_url": model_url,
                "output": output
            }

    async def rig_model(self, original_task_id: str) -> dict:
        """Applies humanoid skeleton rigging to an existing Tripo3D generated model."""
        payload = {
            "type": "rig_model",
            "original_task_id": original_task_id,
            "out_format": "glb"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(f"{self.BASE_URL}/task", headers=self._headers(), json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Tripo3D rig task failed ({res.status_code}): {res.text}")
            data = res.json()
            task_id = data.get("data", {}).get("task_id") or data.get("task_id")
            return {
                "provider": "tripo3d",
                "task_id": task_id,
                "status": "QUEUED",
                "type": "rig_model"
            }

    async def download_asset(self, url: str, output_path: Path) -> Path:
        """Downloads generated asset from Tripo3D CDN."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            res = await client.get(url)
            if res.status_code != 200:
                raise RuntimeError(f"Failed to download asset from {url} ({res.status_code})")
            output_path.write_bytes(res.content)
            logger.info(f"Downloaded 3D asset to {output_path} ({len(res.content)} bytes)")
            return output_path
