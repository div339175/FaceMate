#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import signal

# Calculate BASE_DIR
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Auto-detect and switch to dedicated project virtual environment if invoked outside it
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python")
if os.path.exists(VENV_PYTHON) and os.path.realpath(sys.executable) != os.path.realpath(VENV_PYTHON):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

# Prevent macOS OpenMP crash & thread contention across NumPy, TensorFlow, OpenCV, NumExpr
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KERAS_HOME"] = os.path.join(BASE_DIR, ".keras")
os.environ["DEEPFACE_HOME"] = os.path.join(BASE_DIR, ".deepface")

# Ignore SIGPIPE to prevent macOS socket teardowns from terminating the server process
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "facemate.settings")

    # Default runserver to --noreload on macOS to avoid StatReloader crashing
    # with multi-threaded TensorFlow and OpenCV
    if "runserver" in sys.argv and "--reload" not in sys.argv and "--noreload" not in sys.argv:
        sys.argv.append("--noreload")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

