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

# Fail the deploy rather than the first call: without its index the worker would
# still start, still register as healthy, and answer every question ungrounded.
# That is a worse failure than a red build, because nothing about it looks broken.
#
# This reads the index files directly instead of calling load_index(). The real
# loader builds an embedding model first, which needs OPENAI_API_KEY -- and a key
# has no business being in an image layer. What is worth checking here is what can
# actually go wrong at build time: the index missing from the context, .dockerignore
# quietly excluding it, or a half-written file. A truncated JSON file fails to
# parse, and the counts catch an index that copied but is not the real one.
RUN python -c "\
import json; \
d = json.load(open('index/docstore.json'))['docstore/data']; \
v = json.load(open('index/default__vector_store.json'))['embedding_dict']; \
assert len(d) == len(v), f'docstore has {len(d)} chunks, vector store has {len(v)}'; \
assert len(d) > 500, f'only {len(d)} chunks -- that is not the whole Discourses'; \
print('index loads:', len(d), 'chunks,', len(next(iter(v.values()))), 'dims')"

# Not root. Nothing here needs it.
RUN useradd --create-home --uid 10001 worker && chown -R worker:worker /app
USER worker

# "start" is the production mode: register with LiveKit and wait for work.
# ("dev" is the local mode with reload; "console" talks to it in a terminal.)
CMD ["python", "agent/main.py", "start"]
