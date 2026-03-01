try:
    from prometheus_client import start_http_server, Counter
    _HAVE_PROM = True
except Exception:
    _HAVE_PROM = False


if _HAVE_PROM:
    POLL_COUNTER = Counter("tesla_polls_total", "Number of poll cycles")
    PRODUCE_COUNTER = Counter("tesla_produces_total", "Number of produced messages")
    ERROR_COUNTER = Counter("tesla_errors_total", "Number of polling errors")
else:
    POLL_COUNTER = PRODUCE_COUNTER = ERROR_COUNTER = None
