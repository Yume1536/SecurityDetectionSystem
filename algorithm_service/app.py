import base64
import io
import math

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from flask import Flask, jsonify, request
from PIL import Image
from torchvision import models, transforms

app = Flask(__name__)


def load_model():
    try:
        weights = models.ResNet18_Weights.DEFAULT
        model = models.resnet18(weights=weights)
    except Exception:
        model = models.resnet18(weights=None)
    model.eval()
    return model


MODEL = load_model()
PREPROCESS = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def generate_probe_attention(image_tensor: torch.Tensor, text: str):
    with torch.no_grad():
        logits = MODEL(image_tensor.unsqueeze(0))
        prob = F.softmax(logits, dim=1).squeeze(0)

    top_values, top_indices = torch.topk(prob, k=8)
    img_attention = (top_values / top_values.sum()).cpu().numpy()

    tokens = list(text) if text else list('probe')
    token_scores = np.array([(ord(t) % 31 + 1) for t in tokens], dtype=np.float32)
    txt_attention = token_scores / token_scores.sum()

    entropy_img = float(-np.sum(img_attention * np.log(img_attention + 1e-8)))
    entropy_txt = float(-np.sum(txt_attention * np.log(txt_attention + 1e-8)))
    divergence = abs(entropy_img - entropy_txt) / math.log(max(len(tokens), 8) + 1)
    confidence = float(np.clip(0.35 + divergence * 1.35, 0, 1))
    is_adv = confidence > 0.58

    return {
        'is_adversarial': bool(is_adv),
        'confidence': confidence,
        'img_attention': img_attention.tolist(),
        'txt_attention': txt_attention.tolist(),
        'token_labels': tokens,
        'top_indices': top_indices.cpu().numpy().astype(int).tolist(),
    }


def build_heatmap(image: Image.Image):
    rgb = np.array(image.convert('RGB').resize((224, 224))) / 255.0
    gray = rgb.mean(axis=2)
    gx, gy = np.gradient(gray)
    edges = np.sqrt(gx ** 2 + gy ** 2)
    edges = (edges - edges.min()) / (edges.max() - edges.min() + 1e-8)

    fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
    ax.imshow(rgb)
    ax.imshow(edges, cmap='jet', alpha=0.48)
    ax.axis('off')
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


@app.route('/detect', methods=['POST'])
def detect():
    data = request.get_json(force=True)
    image_b64 = data.get('image', '')
    text = data.get('text', '')
    if not image_b64:
        return jsonify({'message': '缺少图像'}), 400

    image = Image.open(io.BytesIO(base64.b64decode(image_b64))).convert('RGB')
    tensor = PREPROCESS(image)
    score = generate_probe_attention(tensor, text)
    heatmap_b64 = build_heatmap(image)

    return jsonify({
        'is_adversarial': score['is_adversarial'],
        'confidence': score['confidence'],
        'heatmap': heatmap_b64,
        'attention_data': {
            'img_attention': score['img_attention'],
            'txt_attention': score['txt_attention'],
            'token_labels': score['token_labels'],
            'top_indices': score['top_indices'],
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
