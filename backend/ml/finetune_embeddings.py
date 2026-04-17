"""
Script to fine-tune sentence-transformers on biotech data.
Saves fine-tuned model as biotech-embeddings.

Usage:
    uv run python ml/finetune_embeddings.py
"""

import joblib
from sentence_transformers import InputExample, losses, SentenceTransformer
from torch.utils.data import DataLoader

# Load biotech contrastive pairs (replace with your data)
# Example pairs - add more relevant biotech terms
print("Loading biotech contrastive pairs...")
train_examples = [
    InputExample(texts=["biotech research", "biomedical discovery"], label=1.0),
    InputExample(texts=["drug safety", "pharmacovigilance"], label=1.0),
    InputExample(texts=["liver toxicity", "hepatotoxicity"], label=1.0),
    InputExample(texts=["organ-on-chip", "microphysiological system"], label=1.0),
    InputExample(texts=["preclinical ADME", "drug metabolism"], label=1.0),
    InputExample(texts=["biomarker discovery", "clinical biomarker"], label=1.0),
    InputExample(texts=["cell therapy", "regenerative medicine"], label=1.0),
    InputExample(texts=["genome editing", "CRISPR"], label=1.0),
]

# Load base model
print("Loading base model 'all-MiniLM-L6-v2'...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Prepare data loader
print("Preparing data loader...")
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.CosineSimilarityLoss(model)

# Fine-tune model
print("Starting fine-tuning (3 epochs)...")
model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=3,
    output_path="backend/ml/models/biotech-embeddings"
)

# Save fine-tuned model
joblib.dump(model, "backend/ml/models/biotech-embeddings/biotech-embeddings.joblib")

print("✅ Fine-tuned model saved to backend/ml/models/biotech-embeddings/")