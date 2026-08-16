import http from "http";

const server = http.createServer((request, response) => {
    request.setEncoding("utf8");
    process.stdout.write(`${request.method} ${request.url} HTTP/${request.httpVersion}\r\n`)
    for (const [name, value] of Object.entries(request.headers)) {
      process.stdout.write(`${name}: ${value}\r\n`);
    }
    process.stdout.write("\r\n")
    request.on("data", chunk => {
        process.stdout.write(chunk);
    });

    request.on("end", () => {
        response.writeHead(200, {
          "Content-Type": "text/plain"
        });
        response.end("OK\n");
    });
});

const port = 3000;
server.listen(3000, () => {
  console.log(`Listening on http://localhost:${port}`);
});