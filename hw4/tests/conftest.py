import os

# Keep console exporters quiet during tests; they would otherwise try to
# flush into pytest's captured stdout after it is closed.
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
