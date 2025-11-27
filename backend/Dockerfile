FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install webapp requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Plan2Scene dependencies (will be available when repo is mounted)
# These are common dependencies needed by the plan2scene scripts
# Note: Using newer kornia version for Python 3.10 compatibility
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    pyyaml \
    orderedattrdict \
    kornia==0.6.0 \
    shapely \
    tensorboard \
    pytorch-fid==0.1.1 \
    && pip install --no-cache-dir git+https://github.com/sbrisard/moisan2011.git@master

# Set PYTHONPATH to include the plan2scene code directory
ENV PYTHONPATH="/app/plan2scene_core/code/src:${PYTHONPATH}"

# Keep container alive for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
