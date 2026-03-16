FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 1. uv 설치 (공식 이미지에서 복사해오는 가장 깔끔한 방법)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성 패키지 관리 파일을 컨테이너 내부에 복사합니다.
COPY pyproject.toml uv.lock ./

# 3. ai_worker에 필요한 패키지 설치 (app 서비스 재사용을 위해 app 그룹 포함)
RUN uv sync --group ai --group app --no-dev --frozen

# 4. 로컬 소스 코드를 컨테이너 내부로 복사합니다.
COPY ./ai_worker ./ai_worker
COPY ./app ./app

# 5. ai_worker 스케줄러 실행
CMD ["uv", "run", "python", "-m", "ai_worker.main"]
