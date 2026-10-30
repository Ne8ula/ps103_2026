# GPU worker image for the heavy stages (transcribe, perception, render). Build from pipeline/:
#   docker build -f worker/Dockerfile -t tutorialgen-worker .
# Untested on a real GPU host yet; see REMOTE_GPU.md.
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04

# graphics: MediaPipe's GPU delegate uses OpenGL ES via EGL, not CUDA.
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,video \
    PIP_NO_CACHE_DIR=1 \
    TUTORIALGEN_DEVICE=cuda \
    TUTORIALGEN_HOME=/work/projects

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv libegl1 libgles2 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY tutorialgen ./tutorialgen
RUN python3 -m venv /venv && /venv/bin/pip install --upgrade pip && /venv/bin/pip install .
ENV PATH=/venv/bin:$PATH

# Bake the models in so cold starts don't download them.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')" \
    && python -c "from tutorialgen.media.hands import ensure_model; ensure_model(None)"

# The project folder is mounted or synced to /work/projects/<id>; run exactly the requested stages.
ENTRYPOINT ["python", "-m", "tutorialgen", "run"]
CMD ["--help"]
