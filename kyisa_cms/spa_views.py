"""
SPA catch-all view — serves the React index.html for any non-API,
non-admin, non-static URL so client-side routing works in production.

In development, use Vite dev server on :5173.
In production, run `npm run build` in frontend/ then `collectstatic`.
The /app/ route serves the React SPA and lets React Router handle routing.
"""
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404


REACT_BUILD = Path(settings.BASE_DIR) / "frontend" / "dist"
REACT_INDEX = REACT_BUILD / "index.html"


def spa_view(request, path=""):
    """Serve the React SPA.

    For the index route and any sub-path (handled by React Router),
    return index.html.  For static asset requests inside /app/assets/,
    serve the actual file from the build output.
    """
    if not REACT_INDEX.exists():
        raise Http404(
            "React build not found. Run 'npm run build' in the frontend/ directory."
        )

    # If the path points to an actual file in dist/, serve it directly
    if path:
        file_path = REACT_BUILD / path
        if file_path.is_file() and file_path.resolve().is_relative_to(REACT_BUILD.resolve()):
            return FileResponse(open(file_path, "rb"))

    # Otherwise serve index.html for client-side routing
    return HttpResponse(
        REACT_INDEX.read_text(encoding="utf-8"),
        content_type="text/html",
    )
