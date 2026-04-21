const API_BASE = 'http://127.0.0.1:5000/api';
const authCard = document.getElementById('authCard');
const detectCard = document.getElementById('detectCard');
const vizCard = document.getElementById('vizCard');
const historyCard = document.getElementById('historyCard');
const userPanel = document.getElementById('userPanel');
const detectResult = document.getElementById('detectResult');
const historyList = document.getElementById('historyList');
const heatmapImage = document.getElementById('heatmapImage');

let currentUser = JSON.parse(localStorage.getItem('user') || 'null');

function renderAuth() {
  authCard.innerHTML = `
    <h2>用户管理</h2>
    <input id="username" placeholder="用户名" />
    <input id="password" placeholder="密码" type="password" />
    <button id="loginBtn">登录</button>
    <button id="registerBtn" class="small-btn">注册</button>
  `;

  document.getElementById('loginBtn').onclick = login;
  document.getElementById('registerBtn').onclick = register;
}

function updateUserView() {
  if (!currentUser) {
    userPanel.innerHTML = '<b>未登录</b>';
    detectCard.classList.add('hidden');
    vizCard.classList.add('hidden');
    historyCard.classList.add('hidden');
    return;
  }

  userPanel.innerHTML = `
    <span>欢迎，${currentUser.username}</span>
    <button class="small-btn" onclick="logout()">退出</button>
  `;
  detectCard.classList.remove('hidden');
  historyCard.classList.remove('hidden');
  loadHistory();
}

async function login() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();
  if (!res.ok) return alert(data.message || '登录失败');

  currentUser = data.user;
  localStorage.setItem('user', JSON.stringify(currentUser));
  updateUserView();
}

async function register() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();
  alert(data.message || '完成');
}

window.logout = function () {
  localStorage.removeItem('user');
  currentUser = null;
  updateUserView();
};

document.getElementById('detectForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = document.getElementById('imageInput').files[0];
  const text = document.getElementById('textInput').value;
  if (!file) return alert('请先选择图片');

  const formData = new FormData();
  formData.append('user_id', currentUser.id);
  formData.append('text', text);
  formData.append('image', file);

  detectResult.innerText = '检测中，请稍候...';
  const res = await fetch(`${API_BASE}/detect`, { method: 'POST', body: formData });
  const data = await res.json();
  if (!res.ok) return (detectResult.innerText = data.message || '检测失败');

  detectResult.innerHTML = `
    <p><b>结论：</b>${data.is_adversarial ? '疑似对抗样本' : '正常样本'}</p>
    <p><b>置信度：</b>${(data.confidence * 100).toFixed(2)}%</p>
    <button class="small-btn" onclick="downloadReport(${data.record_id})">生成PDF报告</button>
  `;

  if (data.heatmap) {
    heatmapImage.src = `data:image/png;base64,${data.heatmap}`;
  }
  renderChart(data.attention_data);
  vizCard.classList.remove('hidden');
  loadHistory();
});

function renderChart(attentionData) {
  const chart = echarts.init(document.getElementById('chart'));
  const labels = attentionData.token_labels || [];
  const img = (attentionData.img_attention || []).map((v) => Number(v.toFixed(4)));
  const txt = (attentionData.txt_attention || []).slice(0, labels.length).map((v) => Number(v.toFixed(4)));

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['图像注意力', '文本注意力'] },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value' },
    series: [
      { name: '图像注意力', type: 'line', data: img, smooth: true },
      { name: '文本注意力', type: 'line', data: txt, smooth: true },
    ],
  });
}

async function loadHistory() {
  const res = await fetch(`${API_BASE}/records/${currentUser.id}`);
  const items = await res.json();
  historyList.innerHTML = items.length
    ? items
        .map(
          (item) => `
        <div class="history-item">
          <div>
            <div>记录ID：${item.id}</div>
            <div>检测结果：${item.is_adversarial ? '对抗样本' : '正常样本'} | ${(item.confidence * 100).toFixed(2)}%</div>
            <div>时间：${new Date(item.created_at).toLocaleString()}</div>
          </div>
          <div>
            <button class="small-btn" onclick="viewDetail(${item.id})">详情</button>
            <button class="small-btn" onclick="downloadReport(${item.id})">报告</button>
          </div>
        </div>`
        )
        .join('')
    : '<p>暂无记录</p>';
}

window.viewDetail = async function (id) {
  const res = await fetch(`${API_BASE}/records/detail/${id}`);
  const data = await res.json();
  detectResult.innerHTML = `
    <p><b>记录ID：</b>${data.id}</p>
    <p><b>结论：</b>${data.is_adversarial ? '疑似对抗样本' : '正常样本'}</p>
    <p><b>置信度：</b>${(data.confidence * 100).toFixed(2)}%</p>
  `;
  if (data.heatmap) heatmapImage.src = `data:image/png;base64,${data.heatmap}`;
  renderChart(data.attention_data || {});
  vizCard.classList.remove('hidden');
};

window.downloadReport = function (id) {
  window.open(`${API_BASE}/report/${id}`, '_blank');
};

renderAuth();
updateUserView();
