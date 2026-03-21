import base64
import hashlib
from pathlib import Path
from typing import Optional, Tuple


def get_file_url(api_key, file_id, file_path):
    """Construct the full URL to download a file"""
    return f"https://nitaku.onlyoffice.com/download?file={file_id}"


def download_file(api_key, file_url, filename):
    """Download file from OnlyOffice URL with basic error handling"""
    import requests
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(file_url, headers=headers)
    response.raise_for_status()
    with open(filename, 'wb') as f:
        f.write(response.content)
    return filename


def get_mime_type_from_url(url: str) -> str:
    """Extract MIME type from URL extension"""
    EXTENSION_TO_MIME = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.bmp': 'image/bmp',
    }
    url_lower = url.lower()
    for ext, mime in EXTENSION_TO_MIME.items():
        if url_lower.endswith(ext):
            return mime
    return 'application/octet-stream'


def download_image(url: str) -> Tuple[bytes, Optional[str]]:
    """Download image from URL.
    
    Returns:
        Tuple of (image_bytes, mime_type)
        mime_type is derived from Content-Type header, falls back to URL extension
    """
    import requests
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    content_type = response.headers.get('Content-Type', '')
    if content_type and 'image/' in content_type:
        mime_type = content_type.split(';')[0].strip()
    else:
        mime_type = get_mime_type_from_url(url)
    
    return response.content, mime_type


def get_image_cache_dir() -> Path:
    """Get or create the image cache directory."""
    cache_dir = Path('cache/images')
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_image_cache_key(url: str) -> str:
    """Generate a cache key from URL (hash-based)."""
    return hashlib.md5(url.encode()).hexdigest()


def get_cached_image_path(url: str) -> Path:
    """Get the path for a cached image."""
    cache_dir = get_image_cache_dir()
    cache_key = get_image_cache_key(url)
    return cache_dir / f"{cache_key}.cache"


def get_cached_image(url: str) -> Optional[Tuple[bytes, str]]:
    """Get image from cache if available.
    
    Returns:
        Tuple of (image_bytes, mime_type) if cached, None otherwise
    """
    cache_path = get_cached_image_path(url)
    if cache_path.exists():
        mime_path = cache_path.with_suffix('.mime')
        if mime_path.exists():
            with open(cache_path, 'rb') as f:
                image_bytes = f.read()
            with open(mime_path, 'r') as f:
                mime_type = f.read().strip()
            return image_bytes, mime_type
    return None


def cache_image(url: str, image_bytes: bytes, mime_type: str) -> None:
    """Cache downloaded image to disk."""
    cache_path = get_cached_image_path(url)
    mime_path = cache_path.with_suffix('.mime')
    with open(cache_path, 'wb') as f:
        f.write(image_bytes)
    with open(mime_path, 'w') as f:
        f.write(mime_type)


def download_image_cached(url: str) -> Tuple[bytes, str]:
    """Download image with caching.
    
    Returns:
        Tuple of (image_bytes, mime_type)
    """
    cached = get_cached_image(url)
    if cached is not None:
        return cached
    
    image_bytes, mime_type = download_image(url)
    cache_image(url, image_bytes, mime_type)
    return image_bytes, mime_type


def image_to_data_uri(image_bytes: bytes, mime_type: str) -> str:
    """Convert image bytes to base64 data URI."""
    b64_data = base64.b64encode(image_bytes).decode('ascii')
    return f"data:{mime_type};base64,{b64_data}"