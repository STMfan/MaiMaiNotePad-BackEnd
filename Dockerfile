FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 不用 apt，直接 pip
COPY MaiMaiNotePad-BackEnd/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY MaiMaiNotePad-BackEnd/ ./

# 预创建常用目录，避免挂载卷时缺失
RUN mkdir -p /app/data /app/logs /app/uploads

EXPOSE 9278

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9278"]

