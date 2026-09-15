#!/bin/bash
# FaceMate Robust Runner Script
# Ensures FaceMate always runs with the project's dedicated virtualenv
# regardless of active Conda or base environments.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "❌ Project virtualenv python not found at $PYTHON"
    exit 1
fi

export KMP_DUPLICATE_LIB_OK="TRUE"
export OMP_NUM_THREADS="1"
export NUMEXPR_NUM_THREADS="1"
export OPENBLAS_NUM_THREADS="1"
export MKL_NUM_THREADS="1"
export VECLIB_MAXIMUM_THREADS="1"
export TF_CPP_MIN_LOG_LEVEL="2"
export CUDA_VISIBLE_DEVICES="-1"
export KERAS_HOME="$DIR/.keras"
export DEEPFACE_HOME="$DIR/.deepface"

CMD="${1:-runserver}"
shift || true

echo "🚀 Starting FaceMate with dedicated environment..."
if [ "$CMD" = "runserver" ]; then
    case " $* " in
        *" --reload "*) exec "$PYTHON" "$DIR/manage.py" "$CMD" "$@" ;;
        *" --noreload "*) exec "$PYTHON" "$DIR/manage.py" "$CMD" "$@" ;;
        *) exec "$PYTHON" "$DIR/manage.py" "$CMD" --noreload "$@" ;;
    esac
else
    exec "$PYTHON" "$DIR/manage.py" "$CMD" "$@"
fi

