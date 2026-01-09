"""
VERITAS - Deepfake Detection Model Training
With CHECKPOINT SUPPORT (pause/resume anytime!)
"""

import torch
import torch.nn as nn
from torch.utils.data import IterableDataset, DataLoader
from torchvision import transforms
from datasets import load_dataset
from transformers import ViTForImageClassification, ViTImageProcessor
from tqdm import tqdm
import os
import json

# ============================================
# CONFIGURATION
# ============================================

CONFIG = {
    "dataset": "prithivMLmods/Deepfake-vs-Real-60K",
    "model_name": "google/vit-base-patch16-224",
    "batch_size": 16,
    "learning_rate": 2e-5,
    "num_epochs": 3,
    "num_labels": 2,
    "save_path": "models/deepfake_detector",
    "checkpoint_path": "checkpoints",
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "max_samples_per_epoch": 10000,  # Full training set
    "save_every_n_batches": 1,      # Checkpoint every batch
}

print(f"🖥️  Using device: {CONFIG['device']}")


# ============================================
# STREAMING DATASET WRAPPER
# ============================================

class StreamingDeepfakeDataset(IterableDataset):
    def __init__(self, split="train", max_samples=None, skip_samples=0):
        self.dataset = load_dataset(
            CONFIG["dataset"],
            split=split,
            streaming=True
        )
        self.max_samples = max_samples
        self.skip_samples = skip_samples  # For resuming
        self.processor = ViTImageProcessor.from_pretrained(CONFIG["model_name"])
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=self.processor.image_mean,
                std=self.processor.image_std
            )
        ])
    
    def __iter__(self):
        count = 0
        skipped = 0
        
        for sample in self.dataset:
            # Skip samples if resuming
            if skipped < self.skip_samples:
                skipped += 1
                continue
                
            if self.max_samples and count >= self.max_samples:
                break
            
            try:
                image = sample["image"]
                label = sample["label"]
                
                if image.mode != "RGB":
                    image = image.convert("RGB")
                
                image_tensor = self.transform(image)
                yield image_tensor, label
                count += 1
                
            except Exception as e:
                continue


# ============================================
# CHECKPOINT FUNCTIONS
# ============================================

def save_checkpoint(model, optimizer, epoch, batch_idx, samples_processed, loss, acc):
    """Save training checkpoint"""
    os.makedirs(CONFIG["checkpoint_path"], exist_ok=True)
    
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "epoch": epoch,
        "batch_idx": batch_idx,
        "samples_processed": samples_processed,
        "loss": loss,
        "acc": acc,
    }
    
    path = os.path.join(CONFIG["checkpoint_path"], "latest_checkpoint.pt")
    torch.save(checkpoint, path)
    
    # Save metadata as JSON for easy reading
    meta = {
        "epoch": epoch,
        "batch_idx": batch_idx,
        "samples_processed": samples_processed,
        "loss": loss,
        "acc": acc,
    }
    with open(os.path.join(CONFIG["checkpoint_path"], "checkpoint_info.json"), "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"\n💾 Checkpoint saved! (Epoch {epoch+1}, Batch {batch_idx}, {samples_processed} samples)")


def load_checkpoint(model, optimizer):
    """Load checkpoint if exists"""
    path = os.path.join(CONFIG["checkpoint_path"], "latest_checkpoint.pt")
    
    if os.path.exists(path):
        print("📂 Found checkpoint, loading...")
        checkpoint = torch.load(path, map_location=CONFIG["device"])
        
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        
        return {
            "epoch": checkpoint["epoch"],
            "batch_idx": checkpoint["batch_idx"],
            "samples_processed": checkpoint["samples_processed"],
        }
    
    return None


# ============================================
# MODEL SETUP
# ============================================

def create_model():
    model = ViTForImageClassification.from_pretrained(
        CONFIG["model_name"],
        num_labels=CONFIG["num_labels"],
        ignore_mismatched_sizes=True
    )
    return model.to(CONFIG["device"])


# ============================================
# TRAINING LOOP
# ============================================

def train_epoch(model, dataloader, optimizer, criterion, epoch, start_batch=0):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    progress = tqdm(enumerate(dataloader), desc=f"Epoch {epoch+1}")
    
    for batch_idx, (images, labels) in progress:
        if batch_idx < start_batch:
            continue
            
        images = images.to(CONFIG["device"])
        labels = labels.to(CONFIG["device"])
        
        optimizer.zero_grad()
        outputs = model(images).logits
        loss = criterion(outputs, labels)
        
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        _, predicted = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total += labels.size(0)
        
        acc = 100 * correct / total if total > 0 else 0
        
        progress.set_postfix({
            "loss": f"{loss.item():.4f}",
            "acc": f"{acc:.2f}%"
        })
        
        # Save checkpoint periodically
        if (batch_idx + 1) % CONFIG["save_every_n_batches"] == 0:
            save_checkpoint(model, optimizer, epoch, batch_idx, total, loss.item(), acc)
    
    return total_loss / max(1, batch_idx + 1), correct / max(1, total)


# ============================================
# MAIN TRAINING FUNCTION
# ============================================

def train():
    print("=" * 50)
    print("🔥 VERITAS Deepfake Detection Training")
    print("=" * 50)
    print(f"📊 Dataset: {CONFIG['dataset']} (STREAMING)")
    print(f"🧠 Model: {CONFIG['model_name']}")
    print(f"🔄 Epochs: {CONFIG['num_epochs']}")
    print(f"📦 Samples per epoch: {CONFIG['max_samples_per_epoch']}")
    print(f"� Checkpoint every: {CONFIG['save_every_n_batches']} batches")
    print("=" * 50)
    
    # Create model
    print("\n🧠 Loading ViT model...")
    model = create_model()
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG["learning_rate"])
    criterion = nn.CrossEntropyLoss()
    
    # Try to resume from checkpoint
    start_epoch = 0
    start_batch = 0
    resume_info = load_checkpoint(model, optimizer)
    
    if resume_info:
        start_epoch = resume_info["epoch"]
        start_batch = resume_info["batch_idx"] + 1
        print(f"▶️  Resuming from Epoch {start_epoch+1}, Batch {start_batch}")
    
    print("\n🚀 Starting training...\n")
    
    for epoch in range(start_epoch, CONFIG["num_epochs"]):
        print(f"\n--- Epoch {epoch + 1}/{CONFIG['num_epochs']} ---")
        
        skip = start_batch * CONFIG["batch_size"] if epoch == start_epoch else 0
        
        train_dataset = StreamingDeepfakeDataset(
            split="train",
            max_samples=CONFIG["max_samples_per_epoch"],
            skip_samples=skip
        )
        train_loader = DataLoader(
            train_dataset,
            batch_size=CONFIG["batch_size"],
            num_workers=0
        )
        
        loss, acc = train_epoch(
            model, train_loader, optimizer, criterion, epoch,
            start_batch=start_batch if epoch == start_epoch else 0
        )
        
        print(f"✅ Epoch {epoch + 1} - Loss: {loss:.4f}, Accuracy: {acc*100:.2f}%")
        
        # Save at end of epoch
        save_checkpoint(model, optimizer, epoch, 0, CONFIG["max_samples_per_epoch"], loss, acc)
        
        start_batch = 0  # Reset for next epoch
    
    # Save final model
    os.makedirs(CONFIG["save_path"], exist_ok=True)
    model.save_pretrained(CONFIG["save_path"])
    print(f"\n🎉 Training complete! Model saved to {CONFIG['save_path']}")
    
    return model


if __name__ == "__main__":
    train()
