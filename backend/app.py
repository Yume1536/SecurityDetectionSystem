import base64
import hashlib
import io
import os
import uuid
from datetime import datetime

import requests
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from config import Config
from models import DetectionRecord, User, db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['HEATMAP_FOLDER'], exist_ok=True)
    os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()

    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = request.get_json(force=True)
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        if not username or not password:
            return jsonify({'message': '用户名和密码不能为空'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'message': '用户已存在'}), 409

        pwd_md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
        user = User(username=username, password_md5=pwd_md5)
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': '注册成功'})

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json(force=True)
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        pwd_md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
        user = User.query.filter_by(username=username, password_md5=pwd_md5).first()
        if not user:
            return jsonify({'message': '用户名或密码错误'}), 401

        return jsonify({
            'message': '登录成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'created_at': user.created_at.isoformat()
            }
        })

    @app.route('/api/detect', methods=['POST'])
    def detect():
        user_id = request.form.get('user_id', type=int)
        text = request.form.get('text', '')
        image_file = request.files.get('image')

        if not user_id:
            return jsonify({'message': '缺少用户ID'}), 400
        if not image_file:
            return jsonify({'message': '请上传图片'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': '用户不存在'}), 404

        ext = os.path.splitext(image_file.filename or 'upload.png')[1] or '.png'
        image_name = f"{uuid.uuid4().hex}{ext}"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
        image_file.save(image_path)

        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        try:
            algo_resp = requests.post(
                f"{app.config['ALGO_SERVICE_URL']}/detect",
                json={'image': image_b64, 'text': text},
                timeout=30,
            )
            algo_resp.raise_for_status()
            result = algo_resp.json()
        except requests.RequestException as exc:
            return jsonify({'message': f'算法服务调用失败: {exc}'}), 502

        heatmap_b64 = result.get('heatmap', '')
        heatmap_path = None
        if heatmap_b64:
            heatmap_name = f"heatmap_{uuid.uuid4().hex}.png"
            heatmap_path = os.path.join(app.config['HEATMAP_FOLDER'], heatmap_name)
            with open(heatmap_path, 'wb') as f:
                f.write(base64.b64decode(heatmap_b64))

        record = DetectionRecord(
            user_id=user_id,
            image_path=image_path,
            input_text=text,
            is_adversarial=bool(result.get('is_adversarial', False)),
            confidence=float(result.get('confidence', 0.0)),
            heatmap_path=heatmap_path,
            attention_data=result.get('attention_data', {}),
        )
        db.session.add(record)
        db.session.commit()

        return jsonify({
            'record_id': record.id,
            'is_adversarial': record.is_adversarial,
            'confidence': record.confidence,
            'heatmap': heatmap_b64,
            'attention_data': record.attention_data,
            'created_at': record.created_at.isoformat(),
        })

    @app.route('/api/records/<int:user_id>', methods=['GET'])
    def list_records(user_id):
        records = DetectionRecord.query.filter_by(user_id=user_id).order_by(DetectionRecord.created_at.desc()).all()
        return jsonify([
            {
                'id': r.id,
                'is_adversarial': r.is_adversarial,
                'confidence': r.confidence,
                'created_at': r.created_at.isoformat(),
            }
            for r in records
        ])

    @app.route('/api/records/detail/<int:record_id>', methods=['GET'])
    def record_detail(record_id):
        r = DetectionRecord.query.get_or_404(record_id)
        heatmap_b64 = ''
        if r.heatmap_path and os.path.exists(r.heatmap_path):
            with open(r.heatmap_path, 'rb') as f:
                heatmap_b64 = base64.b64encode(f.read()).decode('utf-8')

        return jsonify({
            'id': r.id,
            'user_id': r.user_id,
            'image_path': r.image_path,
            'input_text': r.input_text,
            'is_adversarial': r.is_adversarial,
            'confidence': r.confidence,
            'heatmap': heatmap_b64,
            'attention_data': r.attention_data,
            'created_at': r.created_at.isoformat(),
        })

    @app.route('/api/report/<int:record_id>', methods=['GET'])
    def generate_report(record_id):
        r = DetectionRecord.query.get_or_404(record_id)
        report_name = f"report_{record_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        report_path = os.path.join(app.config['REPORT_FOLDER'], report_name)

        c = canvas.Canvas(report_path, pagesize=A4)
        width, height = A4
        y = height - 40

        c.setFont('Helvetica-Bold', 16)
        c.drawString(40, y, 'Multimodal Adversarial Detection Report')
        y -= 30
        c.setFont('Helvetica', 11)
        lines = [
            f"Record ID: {r.id}",
            f"User ID: {r.user_id}",
            f"Text Input: {r.input_text or 'N/A'}",
            f"Is Adversarial: {r.is_adversarial}",
            f"Confidence: {r.confidence:.4f}",
            f"Created At: {r.created_at.isoformat()}",
            'Analysis: PIP attention divergence indicates cross-modal inconsistency.'
        ]
        for line in lines:
            c.drawString(40, y, line)
            y -= 18

        if os.path.exists(r.image_path):
            y -= 10
            c.setFont('Helvetica-Bold', 12)
            c.drawString(40, y, 'Input Image:')
            y -= 150
            image = Image.open(r.image_path).convert('RGB')
            image.thumbnail((220, 120))
            img_buf = io.BytesIO()
            image.save(img_buf, format='PNG')
            img_buf.seek(0)
            c.drawImage(ImageReader(img_buf), 40, y, width=220, height=120, preserveAspectRatio=True)

        if r.heatmap_path and os.path.exists(r.heatmap_path):
            c.setFont('Helvetica-Bold', 12)
            c.drawString(300, y + 130, 'Perturbation Heatmap:')
            c.drawImage(r.heatmap_path, 300, y, width=220, height=120, preserveAspectRatio=True)

        c.showPage()
        c.save()
        return send_file(report_path, as_attachment=True)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
