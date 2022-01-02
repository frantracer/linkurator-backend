import argparse
import sys
from dataclasses import dataclass
from gunicorn.app.wsgiapp import WSGIApplication  # type: ignore


@dataclass
class Arguments:
    port: int
    workers: int
    debug: bool
    reload: bool


def main():
    args = parse_args()
    run_server(app_path='src.entrypoints.fastapi.app:app',
               port=args.port, workers=args.workers, debug=args.debug, reload=args.reload)


def parse_args() -> Arguments:
    parser = argparse.ArgumentParser("Run the API server")
    parser.add_argument("--port", type=int, default=9000, help="Port to run the server on")
    parser.add_argument("--workers", type=int, default=4, help="Number of workers to run")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--reload", action="store_true", help="Reload server if code changes")
    args = parser.parse_args()

    return Arguments(
        port=args.port,
        workers=args.workers,
        debug=args.debug,
        reload=args.reload,
    )


def run_server(app_path: str, port: int, workers: int, debug: bool, reload: bool):
    sys.argv = [
        'gunicorn', app_path,
        '--workers', f"{workers}",
        '--worker-class', 'uvicorn.workers.UvicornWorker',
        '--bind', f"0.0.0.0:{port}",
        '--access-logfile', '-',
    ]
    if reload:
        sys.argv.append('--reload')
    if debug:
        sys.argv.append('--log-level')
        sys.argv.append('debug')

    app = WSGIApplication()
    app.run()


if __name__ == "__main__":
    main()
