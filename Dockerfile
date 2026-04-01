FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libx11-6 \
    libice6 \
    libegl1 \
    libgles2 \
    libglx0 \
    libgomp1 \
    libglvnd0 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig \
    && if [ ! -f /usr/lib/x86_64-linux-gnu/libGLESv2.so.2 ]; then \
       find / -name "libGLESv2*" 2>/dev/null; \
       ln -sf /usr/lib/x86_64-linux-gnu/libGLESv2.so /usr/lib/x86_64-linux-gnu/libGLESv2.so.2 2>/dev/null || true; \
       ldconfig; \
    fi

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --timeout 300 --workers 1 --threads 4"]
