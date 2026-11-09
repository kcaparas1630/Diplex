# Builds the diplex-core engine image: the engine API from core/, and LibreOffice, unoserver and the fonts from ADR 005.
# The container runs the engine API, which starts its own pool of unoserver instances on localhost (ADR 011).

FROM debian:trixie-slim

# LibreOffice Writer without the GUI, its Python bridge, and the metric-compatible font set.
# The nogui package leaves out Writer's UI definitions, but Writer needs them to open a DOCX
# that has comments: without libreoffice-uiconfig-writer it refuses such files or crashes.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libreoffice-writer-nogui \
      libreoffice-uiconfig-writer \
      python3-uno \
      python3-venv \
      fonts-crosextra-carlito \
      fonts-crosextra-caladea \
      fonts-liberation \
      fonts-liberation2 \
      fonts-dejavu-core \
      fonts-noto-core \
 && rm -rf /var/lib/apt/lists/*

# unoserver must run under the Python that can import uno, so the venv sees system packages
RUN python3 -m venv --system-site-packages /opt/unoserver \
 && /opt/unoserver/bin/pip install --no-cache-dir unoserver==3.7

# The engine, in its own venv on Debian's Python, from uv.lock: dependencies first, so a code change doesn't
# reinstall them, then the package itself, not editable, so the venv doesn't need the source.
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/diplex \
    UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1
WORKDIR /opt/diplex-source
COPY core/pyproject.toml core/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --python /usr/bin/python3
COPY core/diplex ./diplex
RUN uv sync --locked --no-dev --no-editable --python /usr/bin/python3

ENV PATH="/opt/unoserver/bin:/opt/diplex/bin:${PATH}"
COPY --chmod=755 scripts/engine-entrypoint.sh /usr/local/bin/diplex-engine

# LibreOffice and the engine run as an unprivileged user with its own home for the profile
RUN useradd --create-home --uid 10001 diplex
USER diplex
WORKDIR /home/diplex

EXPOSE 8000
CMD ["diplex-engine"]
