import aiohttp
import asyncio
import typing as t
import io
import base64
import tempfile
import contextlib

files = [
    (
        io.BytesIO(b"This is the foo file. its not very long but contains foo."),
        {
            "Content-Type": "application/octet-stream", "custom-header": "foo",
            "Content-Disposition": "attachment; filename*=UTF-8''foo.txt",
        }),
    (
        io.BytesIO(b"This is the bar file. its not very long but contains bar."),
        {
            "Content-Type": "text/plain", "custom-header": "bar",
            "Content-Disposition": "attachment; filename*=UTF-8''bar.txt",
        }),
    (
        io.BytesIO(b"This is the baz file. its not very long but contains baz."),
        {
            "Content-Type": "text/plain", "custom-header": "baz",
            "Content-Disposition": "attachment; filename*=UTF-8''baz.txt",
        }),
]


async def stream_base64(source: t.AsyncIterable[bytes]) -> t.AsyncGenerator[bytes, None]:
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


async def stream_io(source: io.IOBase, chunk_size: int) -> t.AsyncGenerator[bytes, None]:
    while True:
        chunk = source.read(chunk_size)
        if not chunk:
            return
        yield chunk


async def main() -> None:
    writer = aiohttp.MultipartWriter("form-data")
    for descriptor, headers in files:
        writer.append(
            aiohttp.AsyncIterablePayload(
                stream_base64(
                    stream_io(descriptor, 16),
                )
            ),
            headers
        )
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://localhost:8080/import", data=writer, chunked=True) as response:
            print(response.status)


if __name__ == '__main__':
    with contextlib.ExitStack() as stack:
        directories = [
            directory
            for directory in stack.enter_context(tempfile.TemporaryDirectory())
        ]
        files = [

        ]
