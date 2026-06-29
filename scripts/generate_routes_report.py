import os
import sys

# Ensure backend app is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

def main():
    routes = []
    for route in app.routes:
        # Check if it's a regular route
        if hasattr(route, "methods") and hasattr(route, "path"):
            # Exclude standard FastAPI schema endpoints unless they are relevant
            if route.path in ["/openapi.json", "/docs", "/redoc", "/"]:
                continue
            methods = "/".join(sorted(list(route.methods)))
            path = route.path
            # Find the handler function's module
            module = "Unknown"
            if hasattr(route, "endpoint") and route.endpoint:
                module = route.endpoint.__module__
            routes.append((methods, path, module))
            
    # Sort routes by path
    routes.sort(key=lambda x: x[1])
    
    # Write to ROUTES_REPORT.md in both root and backend root
    report_content = "# Registered API Routes\n\n| Method | Path | Module |\n|---|---|---|\n"
    for m, p, mod in routes:
        report_content += f"| {m} | {p} | `{mod}` |\n"
        
    backend_report_path = "ROUTES_REPORT.md"
    root_report_path = "../ROUTES_REPORT.md"
    
    with open(backend_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Generated routes report at {backend_report_path}")
    
    try:
        with open(root_report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Generated routes report at {root_report_path}")
    except Exception as e:
        print(f"Warning: could not write to root path {root_report_path}: {e}")

if __name__ == "__main__":
    main()
