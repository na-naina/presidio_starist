# STARIST Docker Deployment Guide

This guide covers deploying STARIST (Stalking Threat AI Recognition and Identification Support Tool) using Docker with NVIDIA GPU support for air-gapped environments.

## System Requirements

### Hardware
- **CPU**: 4+ cores recommended
- **RAM**: 16 GB minimum (32 GB recommended for large files)
- **Storage**: 20 GB free space (for Docker image and models)
- **GPU**: NVIDIA GPU with CUDA support (RTX 6000 Pro or similar)

### Software
- **OS**: Ubuntu 22.04/24.04 LTS (or Windows 10/11 with WSL2)
- **Docker**: Version 24.0 or later
- **NVIDIA Driver**: Version 530+ (for CUDA 12.1 support)
- **nvidia-container-toolkit**: Required for GPU passthrough

---

## Pre-Installation Setup

### 1. Install NVIDIA Drivers (Ubuntu)

```bash
# Add NVIDIA driver repository
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# Install recommended driver (or specific version)
sudo ubuntu-drivers autoinstall

# Reboot
sudo reboot

# Verify installation
nvidia-smi
```

### 2. Install Docker

```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Verify
docker --version
```

### 3. Install NVIDIA Container Toolkit

```bash
# Add NVIDIA container toolkit repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install
sudo apt update
sudo apt install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU access in Docker
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

---

## Installation

### Option 1: Build from Source (Recommended)

This method builds the Docker image with all ML models pre-downloaded.

```bash
# Clone or copy the project
cd /path/to/presidio_starist

# Build the Docker image (takes 15-30 minutes)
docker compose build

# Verify the image was created
docker images | grep starist
```

### Option 2: Load Pre-built Image

If you have a pre-exported Docker image file:

```bash
# Load the image from tar file
docker load -i starist-gpu.tar

# Verify
docker images | grep starist
```

---

## Running STARIST

### Quick Start (Recommended)

**Linux/Mac:**
```bash
# Make script executable (first time only)
chmod +x docker/start.sh

# Run the startup script
./docker/start.sh
```

**Windows:**
```cmd
# Double-click or run:
docker\start.bat
```

### Manual Start

```bash
# Start the container
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

### Access the Application

Open your web browser to: **http://localhost:8501**

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start STARIST in background |
| `docker compose down` | Stop STARIST |
| `docker compose logs -f` | View live logs |
| `docker compose ps` | Check container status |
| `docker compose restart` | Restart the container |
| `docker compose build --no-cache` | Rebuild image from scratch |

---

## Configuration

### Environment Variables

You can customize behavior by editing `docker-compose.yml`:

```yaml
environment:
  - STREAMLIT_SERVER_PORT=8501      # Web UI port
  - ALLOW_OTHER_MODELS=false        # Enable additional model downloads
```

### Persistent Data (Optional)

To persist uploaded/processed files outside the container, uncomment the volumes section in `docker-compose.yml`:

```yaml
volumes:
  - ./data:/app/data
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs for errors
docker compose logs

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Rebuild the image
docker compose build --no-cache
```

### GPU not detected

```bash
# Verify NVIDIA driver
nvidia-smi

# Check nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Out of memory errors

- Close other applications
- Reduce batch size when processing files
- Consider using smaller ML models (spaCy instead of Flair)

### Port already in use

```bash
# Find process using port 8501
sudo lsof -i :8501

# Or change the port in docker-compose.yml
ports:
  - "8502:8501"  # Use port 8502 instead
```

### Slow first startup

The first startup may take 1-2 minutes while models are loaded into GPU memory. Subsequent requests will be much faster.

---

## Exporting the Docker Image

To transfer the image to an air-gapped machine:

```bash
# Save the image to a tar file
docker save starist:gpu -o starist-gpu.tar

# Compress (optional, saves ~30% space)
gzip starist-gpu.tar

# Copy to USB drive or network share
cp starist-gpu.tar.gz /media/usb/
```

On the target machine:

```bash
# Load the image
gunzip starist-gpu.tar.gz
docker load -i starist-gpu.tar
```

---

## Security Notes

- The container runs as a non-root user (`starist`)
- No external network access required after build
- All ML models are cached locally
- Uploaded files remain in the container unless volumes are configured

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review container logs: `docker compose logs`
3. Contact your system administrator

---

## Version Information

- **CUDA Version**: 12.1
- **Python Version**: 3.10
- **Base Image**: nvidia/cuda:12.1.0-runtime-ubuntu22.04
- **Target GPU**: NVIDIA Blackwell RTX 6000 Pro
