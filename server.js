import http from "node:http";
import Busboy from "@fastify/busboy";

async function*base64Decode(source) {
    let remainder = "";
    for await (const chunk of source) {
        const data = remainder + new TextDecoder().decode(chunk);
        const length = data.length - (data.length % 4);
        if (length > 0) {
            yield Uint8Array.from(
                atob(data.slice(0, length)),
                character => character.charCodeAt(0),
            )
        }
        remainder = data.slice(length);
    }
    if (remainder.length > 0) {
        yield Uint8Array.from(
            atob(remainder),
            character => character.charCodeAt(0),
        )
    }
}

/**
 * @param {import("@fastify/busboy").BusboyFileStream} file
 * @returns {Promise<void>}
 */
async function processFile(file) {
    const chunks = [];
    for await (const chunk of base64Decode(file)) {
        chunks.push(chunk);
    }
    const length = chunks.reduce((result, chunk) => result + chunk.byteLength, 0)
    const bytes = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) {
        bytes.set(chunk, offset)
        offset += chunk.byteLength;
    }
    const text = new TextDecoder("utf-8").decode(bytes);
    console.log(text);
}


const server = http.createServer((request, response) => {
    if (request.url !== "/import") {
        response.writeHead(404);
        response.end("Not found\n");
        return;
    }
    if (request.method !== "POST") {
        response.statusCode = 405;
        response.end("Method not allowed\n");
    }
    const contentType = request.headers["content-type"];
    if (!contentType.match(/.*(multipart)[^\/]*\/.*(form-data).*/)) {
        response.writeHead(400);
        response.end("Expected content-type multipart/form-data\n");
        return;
    }
    const reader = Busboy({
        headers: request.headers,
    })
    reader.on("file", (fieldName, file, info) => {
        processFile(file).catch(error => {
            console.error(error);
            file.resume();
        })
    })
})