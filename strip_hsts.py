from mitmproxy import http

def response(flow: http.HTTPFlow) -> None:
    # remove Strict-Transport-Security header if present
    flow.response.headers.pop("Strict-Transport-Security", None)
