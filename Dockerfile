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

# Seed copies for Docker volume (uploaded_images mount hides bundled files)
RUN mkdir -p /app/ocr_seed && \
    cp /app/uploaded_images/20250213_032806_25143ccc.jpg /app/ocr_seed/ && \
    cp /app/uploaded_images/20250213_141405_e502f390.jpg /app/ocr_seed/ && \
    cp /app/uploaded_images/20250213_151912_2bfbd617.jpeg /app/ocr_seed/

COPY deploy/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 10000

ENTRYPOINT ["/docker-entrypoint.sh"]
