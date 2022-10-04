ARG PYTORCH_IMAGE=nvcr.io/nvidia/pytorch:22.04-py3
FROM ${PYTORCH_IMAGE}

RUN python3 -m pip install -U pip
RUN python3 -m pip install -U setuptools
RUN python3 -m pip install torch torchvision tensorboard nvflare

WORKDIR /workspace/
RUN git clone https://github.com/NVIDIA/NVFlare.git

# Install dependencies missing in this container
# NOTE: container already has matplotlib==3.5.1 tqdm==4.62.0
RUN python -m pip install   azureml-defaults==1.41.0 \
                            mlflow==1.25.1 \
                            azureml-mlflow==1.41.0 \
                            transformers==4.18.0 \
                            psutil==5.9.0 \
                            pynvml==11.4.1
