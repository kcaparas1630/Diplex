# Builds the diplex-core engine image: LibreOffice, unoserver and the fonts from ADR 005.
# For now it runs a single unoserver on localhost; the supervised pool (ADR 004) comes later.

FROM debian:trixie-slim

# LibreOffice Writer without the GUI, its Python bridge, and the metric-compatible font set
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libreoffice-writer-nogui \
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
ENV PATH="/opt/unoserver/bin:${PATH}"

# LibreOffice runs as an unprivileged user with its own home for the profile
RUN useradd --create-home --uid 10001 diplex
USER diplex
WORKDIR /home/diplex

CMD ["unoserver", "--interface", "127.0.0.1", "--uno-interface", "127.0.0.1"]
