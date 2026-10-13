FROM node:24-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS node
FROM ruby:3.4-slim-bookworm@sha256:22165c5f904d76a8a02fbdd419d0269481369523fd66978232d16c88099730e2
ARG OPENCODE_VERSION=1.19.0
ARG RAILS_VERSION=8.1.4
ARG HERDR_VERSION=0.9.3
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev postgresql-client git curl ca-certificates \
    ripgrep jq python3 python3-pip python3-venv libyaml-dev libvips pkg-config openssh-client \
    musl libgcc-s1 libstdc++6 procps less nano tmux \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && npm install -g opencode-ai@${OPENCODE_VERSION} \
    && gem install rails -v ${RAILS_VERSION} --no-document \
    && gem install pg puma --no-document
RUN case "${TARGETARCH}" in arm64) arch=aarch64 ;; amd64) arch=x86_64 ;; *) exit 1 ;; esac \
    && curl --fail --location --retry 3 "https://github.com/herdrdev/herdr/releases/download/v${HERDR_VERSION}/herdr-linux-${arch}" -o /usr/local/bin/herdr \
    && chmod 755 /usr/local/bin/herdr \
    && herdr --version
COPY browser/package.json browser/package-lock.json /opt/browser/
RUN cd /opt/browser && npm ci --omit=dev
COPY browser/cdp.mjs /opt/browser/cdp.mjs
RUN useradd --create-home --uid 1000 --shell /bin/bash dev \
    && mkdir -p /workspace /spec /home/dev/.config/opencode/skills /home/dev/.config/herdr \
       /home/dev/.local/share /home/dev/.local/state /home/dev/.cache /home/dev/bundle \
    && chown -R dev:dev /home/dev /workspace /spec
COPY --chown=dev:dev config/opencode.json /home/dev/.config/opencode/opencode.json
COPY --chown=dev:dev vendor/skills/ /home/dev/.config/opencode/skills/
COPY --chown=dev:dev vendor/MATT-POCOCK-LICENSE /home/dev/.config/opencode/skills/MATT-POCOCK-LICENSE
COPY scripts/entrypoint.sh /usr/local/bin/dev-entrypoint
RUN chmod 755 /usr/local/bin/dev-entrypoint \
    && mkdir -p /opt/cleanroom/seed && chown dev:dev /opt/cleanroom/seed
USER dev
RUN mkdir -p /home/dev/.config/opencode/skills/herdr \
    && herdr --skill > /home/dev/.config/opencode/skills/herdr/SKILL.md \
    && herdr integration install opencode \
    && cp -a /home/dev/.config/opencode /opt/cleanroom/seed/opencode
ENV HOME=/home/dev BUNDLE_PATH=/home/dev/bundle PATH=/home/dev/bundle/bin:$PATH
WORKDIR /workspace
ENTRYPOINT ["dev-entrypoint"]
CMD ["opencode"]
