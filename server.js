import http from "node:http";
import { Readable } from "node:stream";
import { parseMultipartStream } from "mixpart";

let id = 0;
function getId() {
    return id++;
}

const server = http.createServer(async (request, response) => {
    const id = getId();
    console.log(`Request ${id} started...`)
    if (request.url !== "/import") {
        const message = `location ${request.url} not found`;
        console.log(`Request ${id}: ${message}`);
        response.writeHead(404, {
            "Content-Type": "text/plain"
        });
        response.end(`${message}\n`);
        return;
    }
    if (request.method !== "POST") {
        const message = `method ${request.method} not allowed`;
        console.log(`Request ${id}: ${message}`);
        response.writeHead(405, {
            "Content-Type": "text/plain",
        });
        response.end(`${message}\n`);
        return;
    }
    const contentType = request.headers["content-type"];
    if (!contentType?.match(/.*(multipart)[^\/]*\/.*(mixed).*/)) {
        const message = `Expected Content-Type multipart/mixed received ${contentType}`;
        console.log(`Request ${id}: ${message}`);
        response.writeHead(400, {
            "Content-Type": "text/plain",
        });
        response.end(`${message}\n`);
        return;
    }
    await handleRequest(id, request, contentType, response);
});

/**
 * @param {number} id
 * @param {import("node:http").IncomingMessage} request
 * @param {string} contentType
 * @param {import("node:http").ServerResponse} response
 */
async function handleRequest(id, request, contentType, response) {
    console.log(`Request ${id}: Processing request...`);
    console.log(`Request ${id}: Request headers:`, request.headers);

    const multipartResponse = new Response(Readable.toWeb(request), {
        headers: { "Content-Type": contentType },
    });
    try {
        let messageId = 0;
       for await (const message of parseMultipartStream(multipartResponse)) {
           await processMessage(id, messageId++, message);
       }
       const message = "OK";
       console.log(`Request ${id}: ${message}`);
       response.writeHead(200, {
            "content-type": "text/plain",
        });
        response.end(`${message}\n`);
    } catch (error) {
        const message = `Invalid multipart request`;
        console.log(`Request ${id}: ${message}`);
        console.error(error);
        response.writeHead(400, {
            "content-type": "text/plain"
        });
        response.end(`${message}\n`);
    }
}

/**
 * @param {number} id
 * @param {number} messageId
 * @param {import("mixpart").MultipartMessage} message
 * @returns {Promise<void>}
 */
async function processMessage(id, messageId, message) {
    let contentBlock = "";
    const headers = Object.fromEntries(Array.from(message.headers.entries(), ([key, value]) => [key.toLowerCase(), value]));
    const contentTransferEncoding = headers["content-transfer-encoding"];
    const stream = contentTransferEncoding?.toLowerCase() === "base64"
        ? base64Decode(message.payload)
        : message.payload;
    const decoder = new TextDecoder("utf8");
    for await (const chunk of stream) {
        contentBlock += decoder.decode(chunk, { stream: true})
    }
    contentBlock += decoder.decode();
    const headingBlock = `---------- Batch ${id} message ${messageId} ----------`
    const headerBlock = Array.from(message.headers.entries(), ([name, value]) => `${name}: ${value}`).join("\n");
    const log = [
         headingBlock,
        headerBlock,
        "\n",
        contentBlock,
        "-".repeat(headingBlock.length)
    ].join("\n")
    console.log(log);
}




async function*base64Decode(source) {
    const asciiDecoder = new TextDecoder("ascii");
    let remainder = "";
    for await (const chunk of source) {
        const data = remainder + asciiDecoder.decode(chunk, { stream: true});
        const length = data.length - (data.length % 4);
        if (length > 0) {
            yield Uint8Array.from(
                atob(data.slice(0, length)),
                character => character.charCodeAt(0),
            )
        }
        remainder = data.slice(length);
    }
    remainder += asciiDecoder.decode();
    if (remainder.length > 0) {
        yield Uint8Array.from(
            atob(remainder),
            character => character.charCodeAt(0),
        )
    }
}

server.listen(8080, () => {
    console.log("Listening on port 8080");
});
