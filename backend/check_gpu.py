import torch
import sys

def check_gpu():
    if torch.cuda.is_available():
        print(f"✅ GPU is available: {torch.cuda.get_device_name(0)}")
        sys.exit(0)
    else:
        print("❌ GPU is NOT available.")
        sys.exit(1)

if __name__ == "__main__":
    check_gpu()
