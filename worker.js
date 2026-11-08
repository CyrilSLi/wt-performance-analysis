export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        if (url.pathname.endsWith("/data.js")) {
            const acceptEncoding = request.headers.get("Accept-Encoding") || "";
            let object;
            const headers = new Headers();

            if (acceptEncoding.includes("br")) {
                object = await env.MY_BUCKET.get("data.js.br");
                headers.set("Content-Encoding", "br");
            } else {
                object = await env.MY_BUCKET.get("data.js");
            }

            object.writeHttpMetadata(headers);
            headers.set("Content-Type", "application/javascript; charset=utf-8");
            headers.set("etag", object.httpEtag);
            headers.set("Access-Control-Allow-Origin", "*");
            headers.set("Vary", "Accept-Encoding");
            return new Response(object.body, {
                headers,
                encodeBody: "manual"
            });
        }

        return new Response("File Not Found", { status: 404 });
    }
};