# 会话级文件上传功能实施方案

## 现状分析

经过代码调研和数据库查询发现：

### ✅ 系统已有
- **数据库持久化**：157个会话，379条消息
- **完整的会话管理**：RequirementsSession、RequirementsMessage 模型
- **REST API**：完整的会话创建和消息处理接口

### 📝 界面特点
- **单对话模式**：每次选择助手都创建新会话
- **无历史界面**：没有会话列表、历史浏览等UI
- **会话临时性**：用户体验上是"一次性对话"

## 文件上传方案设计

### 核心思路
既然用户体验是"一次性对话"，那么文件上传也应该是**会话级的临时存储**：
- 文件内容存储在当前会话中
- 随会话生命周期管理，无需长期存储
- 简化实现，降低复杂度

### 技术架构

#### 1. 数据库修改（最小化）

```sql
-- 给 RequirementsMessage 表添加一个字段
ALTER TABLE requirements_messages 
ADD COLUMN attached_files TEXT; -- JSON格式存储文件信息
```

#### 2. API修改（扩展现有接口）

```python
# 修改现有的消息发送API
@requirements_bp.route("/sessions/<session_id>/messages", methods=["POST"])
def send_message(session_id):
    """发送消息（支持文件附件）"""
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            # 有文件上传
            message_content = request.form.get('content', '').strip()
            files = request.files.getlist('files')
            attached_files = process_uploaded_files(files)
        else:
            # 纯文本消息
            data = request.get_json()
            message_content = data.get('content', '').strip()
            attached_files = []
        
        # 验证输入
        if not message_content and not attached_files:
            return jsonify({"code": 400, "message": "消息内容或文件不能同时为空"}), 400
        
        # 构建包含文件内容的完整消息
        full_content = build_message_with_files(message_content, attached_files)
        
        # 调用现有AI服务（无需修改）
        ai_service = get_ai_service()
        ai_response = ai_service.process_message(session_id, full_content)
        
        # 保存用户消息（包含文件信息）
        user_message = RequirementsMessage(
            session_id=session_id,
            message_type='user',
            content=message_content,
            attached_files=json.dumps(attached_files) if attached_files else None
        )
        db.session.add(user_message)
        
        # 保存AI响应消息
        ai_message = RequirementsMessage(
            session_id=session_id,
            message_type='ai', 
            content=ai_response['content']
        )
        db.session.add(ai_message)
        db.session.commit()
        
        return jsonify({
            "code": 200,
            "message": "消息发送成功",
            "data": {
                "user_message": user_message.to_dict(),
                "ai_message": ai_message.to_dict()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"发送失败: {str(e)}"}), 500

def process_uploaded_files(files):
    """处理上传的文件，提取内容"""
    attached_files = []
    
    for file in files:
        # 验证文件格式
        if not file.filename.lower().endswith(('.txt', '.md')):
            raise ValueError(f"不支持的文件格式: {file.filename}。仅支持 txt 和 md 文件")
        
        # 验证文件大小（10MB）
        content_bytes = file.read()
        if len(content_bytes) > 10 * 1024 * 1024:
            raise ValueError(f"文件过大: {file.filename}。最大支持 10MB")
        
        # 尝试解码文件内容
        content = None
        for encoding in ['utf-8', 'gbk', 'gb2312']:
            try:
                content = content_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValueError(f"无法解码文件: {file.filename}")
        
        attached_files.append({
            "filename": file.filename,
            "content": content,
            "size": len(content_bytes),
            "encoding": encoding
        })
    
    return attached_files

def build_message_with_files(message_content, attached_files):
    """构建包含文件内容的完整消息"""
    if not attached_files:
        return message_content
    
    parts = ["=== 相关文档内容 ==="]
    
    for file_info in attached_files:
        parts.append(f"\n## 文档：{file_info['filename']}")
        parts.append("```")
        parts.append(file_info['content'])
        parts.append("```\n")
    
    if message_content.strip():
        parts.append("=== 用户问题 ===")
        parts.append(message_content)
    
    return "\n".join(parts)
```

#### 3. 前端实现（基于现有界面）

```html
<!-- 修改现有的输入区域 -->
<div class="input-area">
    <!-- 文件附件预览区域 -->
    <div id="attachmentPreview" class="attachment-preview" style="display: none;">
        <div class="attachment-header">
            <span>已选择的文件</span>
            <button type="button" onclick="clearAllAttachments()" class="clear-all-btn">清除全部</button>
        </div>
        <div id="attachmentList" class="attachment-list"></div>
    </div>
    
    <!-- 现有的消息输入表单 -->
    <form class="input-form" id="messageForm">
        <div class="input-wrapper">
            <textarea 
                class="message-input" 
                id="messageInput" 
                placeholder="请描述项目需求或想法，也可以上传 txt/md 文档"
                maxlength="10000"
                rows="1"
            ></textarea>
            <div class="char-counter">
                <span id="charCount">0</span>/10000
            </div>
        </div>
        
        <div class="input-actions">
            <!-- 文件上传按钮 -->
            <button type="button" onclick="document.getElementById('fileInput').click()" class="file-btn">
                📎 上传文档
            </button>
            
            <!-- 现有的发送按钮 -->
            <button type="submit" class="send-btn" id="sendBtn">发送</button>
        </div>
    </form>
    
    <!-- 隐藏的文件输入 -->
    <input type="file" id="fileInput" multiple accept=".txt,.md" style="display: none;">
</div>
```

```javascript
// 全局变量
let attachedFiles = [];

// 初始化文件上传
function initializeFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const messageInput = document.getElementById('messageInput');
    
    // 文件选择处理
    fileInput.addEventListener('change', handleFileSelect);
    
    // 拖拽上传
    messageInput.addEventListener('dragover', handleDragOver);
    messageInput.addEventListener('dragleave', handleDragLeave);
    messageInput.addEventListener('drop', handleFileDrop);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    processFiles(files);
    e.target.value = ''; // 清空以允许重复选择
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
}

function handleFileDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
}

function processFiles(files) {
    for (const file of files) {
        // 验证文件格式
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!ext.match(/\.(txt|md)$/)) {
            showMessage(`文件 ${file.name} 格式不支持，仅支持 txt 和 md 文件`, 'error');
            continue;
        }
        
        // 验证文件大小
        if (file.size > 10 * 1024 * 1024) {
            showMessage(`文件 ${file.name} 过大，最大支持 10MB`, 'error');
            continue;
        }
        
        // 检查是否已存在
        if (attachedFiles.some(f => f.name === file.name && f.size === file.size)) {
            showMessage(`文件 ${file.name} 已存在`, 'warning');
            continue;
        }
        
        // 读取文件内容
        const reader = new FileReader();
        reader.onload = (e) => {
            const fileInfo = {
                id: Date.now() + Math.random(),
                name: file.name,
                size: file.size,
                content: e.target.result
            };
            
            attachedFiles.push(fileInfo);
            updateAttachmentPreview();
            showMessage(`文件 ${file.name} 上传成功`, 'success');
        };
        
        reader.onerror = () => {
            showMessage(`读取文件 ${file.name} 失败`, 'error');
        };
        
        reader.readAsText(file, 'utf-8');
    }
}

function updateAttachmentPreview() {
    const preview = document.getElementById('attachmentPreview');
    const list = document.getElementById('attachmentList');
    
    if (attachedFiles.length === 0) {
        preview.style.display = 'none';
        return;
    }
    
    preview.style.display = 'block';
    list.innerHTML = attachedFiles.map(file => `
        <div class="attachment-item" data-file-id="${file.id}">
            <div class="attachment-icon">📄</div>
            <div class="attachment-info">
                <div class="attachment-name">${file.name}</div>
                <div class="attachment-size">${formatFileSize(file.size)}</div>
            </div>
            <button onclick="removeAttachment('${file.id}')" class="remove-btn">×</button>
        </div>
    `).join('');
}

function removeAttachment(fileId) {
    attachedFiles = attachedFiles.filter(file => file.id !== fileId);
    updateAttachmentPreview();
}

function clearAllAttachments() {
    attachedFiles = [];
    updateAttachmentPreview();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// 修改现有的发送消息函数
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const content = messageInput.value.trim();
    
    // 检查是否有内容或附件
    if (!content && attachedFiles.length === 0) {
        showMessage('请输入消息内容或上传文件', 'error');
        return;
    }
    
    if (isSending || !currentSessionId) {
        return;
    }
    
    isSending = true;
    updateSendButtonState();
    
    try {
        // 构建FormData
        const formData = new FormData();
        
        if (content) {
            formData.append('content', content);
        }
        
        // 添加文件
        attachedFiles.forEach(fileInfo => {
            const blob = new Blob([fileInfo.content], { type: 'text/plain' });
            formData.append('files', blob, fileInfo.name);
        });
        
        // 立即显示用户消息（包含附件信息）
        const userMessage = {
            message_type: 'user',
            content: content,
            attached_files: attachedFiles.map(f => ({
                filename: f.name,
                size: f.size
            })),
            created_at: new Date().toISOString()
        };
        displayMessage(userMessage);
        
        // 清空输入
        messageInput.value = '';
        messageInput.style.height = 'auto';
        document.getElementById('charCount').textContent = '0';
        attachedFiles = [];
        updateAttachmentPreview();
        updateSendButtonState();
        
        // 显示AI处理动画
        showAiProcessing();
        
        // 发送请求
        const response = await fetch(`/api/requirements/sessions/${currentSessionId}/messages`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            hideAiProcessing();
            if (result.data.ai_message) {
                displayMessage(result.data.ai_message);
            }
        } else {
            throw new Error(result.message || '发送失败');
        }
        
    } catch (error) {
        console.error('发送消息失败:', error);
        hideAiProcessing();
        showMessage('发送失败: ' + error.message, 'error');
    } finally {
        isSending = false;
        updateSendButtonState();
    }
}

// 修改消息显示函数，支持显示附件
function displayMessage(message) {
    const messagesArea = document.getElementById('messagesArea');
    const messageEl = document.createElement('div');
    messageEl.className = `message ${message.message_type}`;
    
    const avatar = message.message_type === 'user' ? '你' : 'AI';
    const time = new Date(message.created_at).toLocaleTimeString();
    
    // 处理消息内容
    let contentHtml;
    if (message.message_type === 'ai' || message.message_type === 'assistant') {
        const extracted = extractProgressContent(message.content);
        if (extracted.hasProgress) {
            updateAnalysisResults(extracted.progressContent);
        }
        contentHtml = parseMarkdown(extracted.cleanedContent);
    } else {
        contentHtml = escapeHtml(message.content);
    }
    
    // 处理附件显示
    let attachmentHtml = '';
    if (message.attached_files) {
        const files = typeof message.attached_files === 'string' 
            ? JSON.parse(message.attached_files) 
            : message.attached_files;
            
        if (files && files.length > 0) {
            attachmentHtml = `
                <div class="message-attachments">
                    ${files.map(file => `
                        <span class="attachment-indicator">
                            📄 ${file.filename} (${formatFileSize(file.size)})
                        </span>
                    `).join('')}
                </div>
            `;
        }
    }
    
    messageEl.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-body">
            <div class="message-content ${message.message_type === 'ai' ? 'ai-formatted' : ''}">${contentHtml}</div>
            ${attachmentHtml}
            <div class="message-footer">
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;
    
    messagesArea.appendChild(messageEl);
    scrollToBottom();
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // ... 现有初始化代码
    initializeFileUpload();
});
```

#### 4. 样式更新

```css
/* 文件附件预览区域 */
.attachment-preview {
    background: #f8f9fa;
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    margin-bottom: 12px;
    padding: 12px;
}

.attachment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #666;
}

.clear-all-btn {
    background: none;
    border: none;
    color: #dc3545;
    font-size: 12px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 3px;
}

.clear-all-btn:hover {
    background: #f5c6cb;
}

.attachment-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.attachment-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    background: white;
    border-radius: 4px;
    border: 1px solid #e8e8e8;
}

.attachment-icon {
    font-size: 14px;
    color: #666;
}

.attachment-info {
    flex: 1;
}

.attachment-name {
    font-size: 13px;
    color: #333;
    font-weight: 500;
}

.attachment-size {
    font-size: 11px;
    color: #999;
}

.remove-btn {
    background: none;
    border: none;
    color: #999;
    font-size: 16px;
    cursor: pointer;
    padding: 0 4px;
    border-radius: 2px;
}

.remove-btn:hover {
    color: #dc3545;
    background: #f8d7da;
}

/* 输入操作区域 */
.input-actions {
    display: flex;
    gap: 8px;
    align-items: center;
}

.file-btn {
    background: #f8f9fa;
    border: 1px solid #e8e8e8;
    color: #666;
    padding: 12px 16px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s ease;
}

.file-btn:hover {
    background: #e9ecef;
    border-color: #d6d9dd;
}

/* 拖拽效果 */
.message-input.drag-over {
    border-color: #007bff;
    background: #f8f9ff;
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

/* 消息中的附件显示 */
.message-attachments {
    margin-top: 8px;
    padding: 6px 8px;
    background: #f8f9fa;
    border-radius: 4px;
    font-size: 12px;
    color: #666;
}

.attachment-indicator {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-right: 12px;
}
```

## 实施计划

### 第一步：数据库扩展（0.5天）
- [ ] 添加 `attached_files` 字段到 `RequirementsMessage` 表
- [ ] 编写数据库迁移脚本
- [ ] 测试数据库修改

### 第二步：API扩展（1天）
- [ ] 修改消息发送API支持文件上传
- [ ] 添加文件处理和验证逻辑
- [ ] 更新消息模型的 `to_dict()` 方法
- [ ] 编写API测试

### 第三步：前端实现（1天）
- [ ] 添加文件上传UI组件
- [ ] 实现拖拽上传功能
- [ ] 修改消息发送逻辑
- [ ] 更新消息显示以支持附件

### 第四步：测试优化（0.5天）
- [ ] 端到端测试
- [ ] 错误处理验证
- [ ] 用户体验优化

**总计：3天**

## 核心优势

1. **最小侵入性**：只添加一个数据库字段，复用现有架构
2. **会话级生命周期**：文件随会话管理，符合现有用户体验
3. **零配置**：无需文件存储系统，无需清理策略
4. **原生集成**：文件内容自动传递给AI，无需修改AI服务
5. **简单维护**：实现简洁，易于维护和扩展

这个方案完美匹配您当前系统的"单对话会话"特性，既实现了文件上传功能，又保持了系统的简洁性！
