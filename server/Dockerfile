# Leaderboard do Tamagoshi Cripto: imagem minúscula, só stdlib.
FROM python:3.12-alpine
WORKDIR /app
COPY ranking.py .
RUN adduser -D pet && mkdir /data && chown pet /data
USER pet
ENV HOST=0.0.0.0 PORT=8740 DB=/data/ranking.db
EXPOSE 8740
VOLUME /data
HEALTHCHECK CMD wget -qO- http://127.0.0.1:8740/health || exit 1
CMD ["python", "ranking.py"]
