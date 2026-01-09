# ============================================
# VERITAS - Deepfake Detection Training (GOOGLE COLAB VERSION)
# ============================================
# 
# HOW TO USE:
# 1. Go to https://colab.research.google.com
# 2. Click "File" → "Upload notebook" OR "File" → "New notebook"
# 3. If new notebook: Copy-paste this entire script into a cell
# 4. Click "Runtime" → "Change runtime type" → Select "GPU"
# 5. Run the cell!
#
# The trained model will be saved to your Google Drive.
# ============================================

# --- STEP 1: Install dependencies ---
!pip install -q torch torchvision transformers datasets tqdm

# --- STEP 2: Mount Google Drive (to save model) ---
from google.colab import drive
drive.mount('/content/drive')

# --- STEP 3: Training Code ---
import torch
import torch.nn as nn
from torch.utils.data import IterableDataset, DataLoader
from torchvision import transforms
from datasets import load_dataset
from transformers import ViTForImageClassification, ViTImageProcessor
from tqdm.notebook import tqdm
import os

# Check GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️ Using: {device}")
if device == "cuda":
    print(f"🎮 GPU: {torch.cuda.get_device_name(0)}")

# Configuration
CONFIG = {
    "dataset": "prithivMLmods/Deepfake-vs-Real-60K",
    "model_name": "google/vit-base-patch16-224",
    "batch_size": 32,  # Larger batch size for GPU
    "learning_rate": 2e-5,
    "num_epochs": 3,
    "num_labels": 2,
    "save_path": "/content/drive/MyDrive/veritas_model",
    "max_samples_per_epoch": 10000,
}

# Streaming Dataset
class StreamingDeepfakeDataset(IterableDataset):
    def __init__(self, split="train", max_samples=None):
        self.dataset = load_dataset(CONFIG["dataset"], split=split, streaming=True)
        self.max_samples = max_samples
        self.processor = ViTImageProcessor.from_pretrained(CONFIG["model_name"])
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=self.processor.image_mean, std=self.processor.image_std)
        ])
    
    def __iter__(self):
        count = 0
        for sample in self.dataset:
            if self.max_samples and count >= self.max_samples:
                break
            try:
                image = sample["image"]
                if image.mode != "RGB":
                    image = image.convert("RGB")
                yield self.transform(image), sample["label"]
                count += 1
            except:
                continue

# Create model
print("🧠 Loading ViT model...")
model = ViTForImageClassification.from_pretrained(
    CONFIG["model_name"],
    num_labels=CONFIG["num_labels"],
    ignore_mismatched_sizes=True
).to(device)

optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG["learning_rate"])
criterion = nn.CrossEntropyLoss()

# Training loop
print("\n🚀 Starting training...\n")

for epoch in range(CONFIG["num_epochs"]):
    print(f"--- Epoch {epoch + 1}/{CONFIG['num_epochs']} ---")
    
    dataset = StreamingDeepfakeDataset(split="train", max_samples=CONFIG["max_samples_per_epoch"])
    loader = DataLoader(dataset, batch_size=CONFIG["batch_size"], num_workers=2)
    
    model.train()
    total_loss, correct, total = 0, 0, 0
    
    for images, labels in tqdm(loader, desc=f"Epoch {epoch+1}"):
        images, labels = images.to(device), labels.to(device)
        
        optimizer.zero_grad()
        outputs = model(images).logits
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        _, predicted = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total += labels.size(0)
    
    acc = 100 * correct / total
    print(f"✅ Epoch {epoch+1} - Loss: {total_loss/len(loader):.4f}, Accuracy: {acc:.2f}%")

# Save to Google Drive
print("\n💾 Saving model to Google Drive...")
os.makedirs(CONFIG["save_path"], exist_ok=True)
model.save_pretrained(CONFIG["save_path"])
print(f"🎉 Done! Model saved to: {CONFIG['save_path']}")
print("\n📥 You can download it from your Google Drive!")
