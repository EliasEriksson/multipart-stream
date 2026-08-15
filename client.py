#!/usr/bin/env python
import aiohttp
import aiofiles
import asyncio
import typing as t
import base64
import tempfile
import contextlib
from pathlib import Path


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


async def main(files: t.Iterable[File]) -> None:
    writer = aiohttp.MultipartWriter("mixed")
    for file in files:
        writer.append(
            aiohttp.AsyncIterablePayload(
                stream_base64(
                    stream_io(file.path, 16),
                )
            ),
            file.meta,
        )
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"http://localhost:8080/import", data=writer, chunked=True
        ) as response:
            print(response.status, await response.text())


if __name__ == "__main__":

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
                    "Content-Disposition": "attachment; filename*=UTF-8''foo.txt",
                },
            ),
            FileData(
                name="bar.txt",
                content='Hellä. This is a small file but it does at least contain the word "bar".',
                meta={
                    "Content-Type": "text/plain; charset=utf-8",
                    "custom-header": "bar",
                    "Content-Disposition": "attachment; filename*=UTF-8''bar.txt",
                },
            ),
            FileData(
                name="baz.txt",
                content='Hellö. This is a small file but it does at least contain the word "baz".',
                meta={
                    "Content-Type": "text/plain; charset=utf-8",
                    "custom-header": "baz",
                    "Content-Disposition": "attachment; filename*=UTF-8''baz.txt",
                },
            ),
        ]
        files = []
        for directory, file in zip(directories, files_data):
            directory.mkdir(parents=True, exist_ok=True)
            with open((path := directory / file.name), "w") as descriptor:
                descriptor.write(file.content)
            files.append(File(path, meta=file.meta))
        asyncio.run(main(files))
