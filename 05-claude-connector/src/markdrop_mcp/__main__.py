import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="markdrop-mcp",
        description="MCP server exposing the md-files-dhivalabs conversion suite (MarkItDown).",
    )
    parser.add_argument(
        "--root",
        action="append",
        default=None,
        metavar="DIR",
        help="Allow file access under DIR (repeatable). Defaults: cwd, ~/Documents, ~/Downloads. "
        "Also configurable via MD_MCP_ROOTS (colon-separated).",
    )
    parser.add_argument("--http", action="store_true", help="Serve Streamable HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=3002, help="HTTP port (default 3002)")
    args = parser.parse_args()

    from . import server
    from .security import Roots

    if args.root:
        server.roots = Roots(args.root)

    if not args.http:
        server.mcp.run()  # stdio
        return

    if args.host not in ("127.0.0.1", "localhost"):
        print(
            "WARNING: binding a non-localhost interface exposes file conversion\n"
            "(within the allowed roots) to the network. Set MD_MCP_TOKEN to require\n"
            "a bearer token.",
            file=sys.stderr,
        )

    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    app = server.mcp.streamable_http_app()

    token = os.getenv("MD_MCP_TOKEN", "")
    if token:
        class TokenAuth(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                auth = request.headers.get("authorization", "")
                if auth != f"Bearer {token}":
                    return JSONResponse({"error": "unauthorized"}, status_code=401)
                return await call_next(request)

        app.add_middleware(TokenAuth)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
