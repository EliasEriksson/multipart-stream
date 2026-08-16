#!/usr/bin/env python
import aiohttp
import aiofiles
import asyncio
import typing as t
import base64
import tempfile
import contextlib
from pathlib import Path
import uuid
import sys
import functools


class File:
    def __init__(self, path: Path, meta: t.Mapping[str, str]) -> None:
        self.path = path
        self.meta = meta


async def stream_base64(
    source: t.AsyncIterable[bytes],
) -> t.AsyncGenerator[bytes, None]:
    remainder = b""
    async for chunk in source:
        if not chunk:
            continue
        chunk = remainder + chunk
        length = len(chunk) - (len(chunk) % 3)
        if length:
            yield base64.b64encode(chunk[:length])
        remainder = chunk[length:]
    if remainder:
        yield base64.b64encode(remainder)


async def stream_io(file: Path, chunk_size: int) -> t.AsyncGenerator[bytes, None]:
    async with aiofiles.open(file, "rb") as descriptor:
        while True:
            chunk = await descriptor.read(chunk_size)
            if not chunk:
                return
            yield chunk


class Payload:
    _boundary: str

    def __init__(self) -> None:
        self._boundary = uuid.uuid4().hex

    @functools.cached_property
    def boundary(self) -> bytes:
        return self._boundary.encode("ascii")

    @functools.cached_property
    def open_boundary(self) -> bytes:
        return b"--%s\r\n" % self.boundary

    @functools.cached_property
    def close_boundary(self) -> bytes:
        return b"--%s--\r\n" % self.boundary

    @property
    def headers(self) -> t.Mapping[str, str]:
        return {"Content-Type": f"multipart/mixed; boundary={self._boundary}"}

    async def from_files(
        self, files: t.Iterable[File]
    ) -> t.AsyncGenerator[bytes, None]:
        index = 0
        for file in files:
            yield self.open_boundary
            headers = b"".join(
                f"{key}: {value}\r\n".encode("latin1")
                for key, value in {
                    **file.meta,
                    f"Content-Disposition": f"attachment; filename*=UTF-8''{file.path.name}",
                    f"Content-Transfer-Encoding": f"base64",
                }.items()
            )
            yield b"%s\r\n" % headers
            stream = stream_base64(
                stream_io(file.path, 16),
            )
            async for chunk in stream:
                yield chunk
            yield b"\r\n"
            index += 1
        yield self.close_boundary


async def main(port: str, files: t.Iterable[File]) -> None:
    payload = Payload()
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"http://localhost:{port}/import",
            data=payload.from_files(files),
            headers=payload.headers,
            chunked=True,
        ) as response:
            print(response.status, await response.text())


if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "8080"

    class FileData:
        def __init__(
            self,
            name: str,
            content: str,
            meta: t.Mapping[str, str] | None = None,
        ) -> None:
            self.name = name
            self.content = content
            self.meta = meta or {}

    with contextlib.ExitStack() as stack:
        directories = [
            Path(stack.enter_context(tempfile.TemporaryDirectory())) for _ in range(3)
        ]
        files_data = [
            FileData(
                name="foo.txt",
                content='Hallå. This is a small file but it does at least contain the word "foo".',
                meta={
                    "Content-Type": "text/plain; charset=utf-8",
                    "custom-header": "foo",
                },
            ),
            FileData(
                name="bar.txt",
                content='Hellä. This is a small file but it does at least contain the word "bar".',
                meta={
                    "Content-Type": "text/plain; charset=utf-8",
                    "custom-header": "bar",
                },
            ),
            FileData(
                name="baz.txt",
                content='Hellö. This is a small file but it does at least contain the word "baz".',
                meta={
                    "Content-Type": "text/plain; charset=utf-8",
                    "custom-header": "baz",
                },
            ),
        ]
        files = []
        for directory, file in zip(directories, files_data):
            directory.mkdir(parents=True, exist_ok=True)
            with open((path := directory / file.name), "w") as descriptor:
                descriptor.write(file.content)
            files.append(File(path, meta=file.meta))
        asyncio.run(main(port, (file for file in files)))
