# The agent worker: one long-running Python process that registers with LiveKit
# and waits to be dispatched into a room.
#
# It is not serverless and cannot be. A LiveKit agent holds a WebRTC connection
# for the length of a call, so it has to be a process that stays up. That single
# fact decides the whole hosting story in the README.
#
# The built image carries the index with it. Downloading a vector store at boot
# would mean a cold worker takes seconds to become useful and can fail for
# reasons that have nothing to do with this project.

FROM python:3.12-slim

# libgomp is what onnxruntime needs at runtime -- the local voice-activity and
# turn-detection models are onnx, and without it the import fails at start.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so editing the agent does not reinstall torch-sized wheels.
COPY pyproject.toml ./

# The compiler is installed, used, and removed inside one layer. It is needed
# because pystemmer -- the word-stemmer under the BM25 keyword index -- ships as
# C source with no prebuilt wheel for this image, so pip has to compile it. It is
# removed again because a compiler in a running container is a liability, not a
# feature. Doing all three in one RUN is what keeps it out of the final image;
# split across layers, the "removal" would delete nothing.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev \
    && pip install --upgrade pip && pip install . \
    && apt-get purge -y --auto-remove gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY agent/ ./agent/
COPY index/ ./index/

# Pull the model files (Silero voice activity detection, the turn detector) into
# the image at build time. Doing this at boot instead would add a download to
# every cold start and make startup depend on someone else's CDN.
RUN python agent/main.py download-files

# Fail the deploy rather than the first call: if the index cannot be loaded, the
# worker would start, register as healthy, and answer every question ungrounded.
RUN python -c "from agent.retrieval.search.index_store import load_index; \
    i = load_index(); print('index loads:', len(i.docstore.docs), 'chunks')"

# Not root. Nothing here needs it.
RUN useradd --create-home --uid 10001 worker && chown -R worker:worker /app
USER worker

# "start" is the production mode: register with LiveKit and wait for work.
# ("dev" is the local mode with reload; "console" talks to it in a terminal.)
CMD ["python", "agent/main.py", "start"]
