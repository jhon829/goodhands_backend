FROM python:3.13-slim

WORKDIR /app

# MariaDB/MySQL 클라이언트 및 빌드 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY app/ ./app/
COPY uploads/ ./uploads/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY .env.docker ./.env

# 실행 권한 설정
RUN mkdir -p uploads logs
RUN chmod 755 uploads logs

# 포트 노출
EXPOSE 10007

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10007"]