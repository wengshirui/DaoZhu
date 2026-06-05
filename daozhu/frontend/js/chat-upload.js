/**
 * chat-upload.js — 文件上传模块（挂载到 Chat 对象）
 */

Chat._uploadedFiles = [];

Chat._bindFileUpload = function() {
  const fileInput = document.getElementById('chat-file');
  if (!fileInput) return;

  fileInput.addEventListener('change', async () => {
    const files = Array.from(fileInput.files);
    if (!files.length) return;

    for (const file of files) {
      await Chat._processUploadedFile(file);
    }
    fileInput.value = ''; // 所有文件处理完后再清空
  });
};

Chat._processUploadedFile = async function(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json();
      App.showToast(`${file.name}: ${err.detail || '上传失败'}`);
      return;
    }

    const data = await res.json();
    Chat._uploadedFiles.push({ name: file.name, content: data.content });
    Chat._renderFileChips();
    Panel.addLog('info', `📎 已解析: ${file.name} (${data.chars} 字)`);
  } catch (e) {
    App.showToast(`文件处理失败: ${e.message}`);
  }
};

Chat._renderFileChips = function() {
  let container = document.getElementById('file-chips');
  if (!container) {
    container = document.createElement('div');
    container.id = 'file-chips';
    container.className = 'file-chips';
    const form = document.getElementById('chat-form');
    form.parentElement.insertBefore(container, form);
  }
  if (Chat._uploadedFiles.length === 0) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = Chat._uploadedFiles.map((f, i) => `
    <span class="file-chip">
      📎 ${f.name}
      <button class="file-chip__remove" onclick="Chat._removeFile(${i})">✕</button>
    </span>
  `).join('');
};

Chat._removeFile = function(index) {
  Chat._uploadedFiles.splice(index, 1);
  Chat._renderFileChips();
};
