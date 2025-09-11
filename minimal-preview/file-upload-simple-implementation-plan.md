# 文件上传功能实施计划（简化版）- 基于现有架构

## 项目概述

基于现有的需求分析系统架构，为智能助手添加文件上传功能，支持用户上传txt和md格式文档，将文件内容作为对话上下文传递给AI。

### 核心发现
经过代码调研发现：
- ✅ **系统已有会话存储**：RequirementsSession 和 RequirementsMessage 模型
- ✅ **系统已有数据库**：完整的SQLAlchemy配置和迁移脚本
- ✅ **系统已有API**：完整的REST API端点和服务层
- ✅ **系统已有AI集成**：IntelligentAssistantService 和完整的AI服务

### 调整后的方案
基于现有架构，采用**轻量级文件上传**方案：
- **临时存储**：文件内容临时关联到当前会话
- **最小化存储**：不需要长期文件存储，重点是将内容传递给AI
- **复用现有架构**：利用现有的消息系统和AI服务

## 技术实现方案

### 1. 数据库扩展（最小化）

只需要给现有的 `RequirementsMessage` 模型添加一个字段：

```python path=/Users/huian@thoughtworks.com/Program/intent-test-framework/web_gui/models.py start=null
# 在 RequirementsMessage 模型中添加字段
class RequirementsMessage(db.Model):
    # ... 现有字段 ...
    
    # 新增：文件附件信息（JSON格式存储）
    attached_files = db.Column(db.Text)  # JSON: [{"filename": "x.txt", "content": "...", "size": 123}]
```

### 2. API扩展（最小化）

修改现有的消息发送API支持文件：

```python path=/Users/huian@thoughtworks.com/Program/intent-test-framework/web_gui/api/requirements.py start=null
@requirements_bp.route("/sessions/<session_id>/messages", methods=["POST"])
def send_message(session_id):
    """发送消息（支持文件附件）"""
    try:
        # 支持两种内容类型
        if request.content_type.startswith('multipart/form-data'):
            # 有文件上传
            message_content = request.form.get('message', '').strip()
            files = request.files.getlist('files')
            attached_files = process_uploaded_files(files)  # 处理文件
        else:
            # 纯文本消息
            data = request.get_json()
            message_content = data.get('content', '').strip()
            attached_files = []
        
        # 构建完整的消息内容（文件内容 + 用户消息）
        full_content = build_message_with_files(message_content, attached_files)
        
        # 调用现有的AI服务（无需修改）
        ai_service = get_ai_service()
        ai_response = ai_service.process_message(session_id, full_content)
        
        # 保存消息（包含文件信息）
        message = RequirementsMessage(
            session_id=session_id,
            message_type='user',
            content=message_content,  # 原始用户消息
            attached_files=json.dumps(attached_files) if attached_files else None
        )
        
        # ... 保存并返回
        
    except Exception as e:
        return standard_error_response(str(e))

def process_uploaded_files(files):
    """处理上传的文件，提取内容"""
    attached_files = []
    
    for file in files:
        # 验证文件格式
        if not file.filename.lower().endswith(('.txt', '.md')):
            raise ValidationError(f"不支持的文件格式: {file.filename}")
        
        # 验证文件大小
        if file.content_length and file.content_length > 10 * 1024 * 1024:  # 10MB
            raise ValidationError(f"文件过大: {file.filename}")
        
        # 读取文件内容
        try:
            content_bytes = file.read()
            # 尝试不同编码
            for encoding in ['utf-8', 'gbk', 'gb2312']:
                try:
                    content = content_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValidationError(f"无法解码文件: {file.filename}")
            
            attached_files.append({
                "filename": file.filename,
                "content": content,
                "size": len(content_bytes),
                "encoding": encoding
            })
            
        except Exception as e:
            raise ValidationError(f"读取文件失败: {file.filename}")
    
    return attached_files

def build_message_with_files(message_content, attached_files):
    """构建包含文件内容的完整消息"""
    if not attached_files:
        return message_content
    
    parts = []
    
    # 添加文件内容部分
    parts.append("=== 附件内容 ===")
    for file_info in attached_files:
        parts.append(f"\n## 文件：{file_info['filename']}")
        parts.append(f"```")
        parts.append(file_info['content'])
        parts.append(f"```\n")
    
    # 添加用户消息部分
    if message_content.strip():
        parts.append("=== 用户问题 ===")
        parts.append(message_content)
    
    return "\n".join(parts)
```

### 3. 前端实现（完全基于现有页面）

修改 `web_gui/templates/requirements_analyzer.html`：

```javascript path=/Users/huian@thoughtworks.com/Program/intent-test-framework/web_gui/templates/requirements_analyzer.html start=null
// 在现有的sendMessage函数基础上修改

// 全局变量存储附件
let attachedFiles = [];

// 文件上传处理
function setupFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const attachmentList = document.getElementById('attachmentList');
    const messageInput = document.getElementById('messageInput');
    
    // 点击上传
    uploadBtn.addEventListener('click', () => {
        fileInput.click();
    });
    
    // 文件选择处理
    fileInput.addEventListener('change', (e) => {
        handleFiles(Array.from(e.target.files));
        e.target.value = ''; // 清空input以允许重复选择同一文件
    });
    
    // 拖拽上传
    messageInput.addEventListener('dragover', (e) => {
        e.preventDefault();
        messageInput.classList.add('drag-over');
    });
    
    messageInput.addEventListener('dragleave', (e) => {
        e.preventDefault();
        messageInput.classList.remove('drag-over');
    });
    
    messageInput.addEventListener('drop', (e) => {
        e.preventDefault();
        messageInput.classList.remove('drag-over');
        handleFiles(Array.from(e.dataTransfer.files));
    });
}

function handleFiles(files) {
    for (const file of files) {
        // 验证文件格式
        if (!file.name.toLowerCase().endsWith('.txt') && !file.name.toLowerCase().endsWith('.md')) {
            showMessage('错误：只支持 .txt 和 .md 格式的文件', 'error');
            continue;
        }
        
        // 验证文件大小
        if (file.size > 10 * 1024 * 1024) {
            showMessage(`错误：文件 ${file.name} 过大，最大支持 10MB`, 'error');
            continue;
        }
        
        // 读取文件内容
        const reader = new FileReader();
        reader.onload = (e) => {
            const fileInfo = {
                name: file.name,
                size: file.size,
                content: e.target.result,
                id: Date.now() + Math.random() // 临时ID
            };
            
            attachedFiles.push(fileInfo);
            updateAttachmentList();
            showMessage(`文件 ${file.name} 上传成功`, 'success');
        };
        
        reader.onerror = () => {
            showMessage(`错误：无法读取文件 ${file.name}`, 'error');
        };
        
        reader.readAsText(file, 'utf-8');
    }
}

function updateAttachmentList() {
    const attachmentList = document.getElementById('attachmentList');
    
    if (attachedFiles.length === 0) {
        attachmentList.style.display = 'none';
        return;
    }
    
    attachmentList.style.display = 'block';
    attachmentList.innerHTML = attachedFiles.map(file => `
        <div class="attachment-item" data-file-id="${file.id}">
            <i class="attachment-icon">📎</i>
            <span class="attachment-name">${file.name}</span>
            <span class="attachment-size">(${formatFileSize(file.size)})</span>
            <button class="remove-attachment" onclick="removeAttachment('${file.id}')">×</button>
        </div>
    `).join('');
}

function removeAttachment(fileId) {
    attachedFiles = attachedFiles.filter(file => file.id !== fileId);
    updateAttachmentList();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// 修改现有的sendMessage函数
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const content = messageInput.value.trim();
    
    // 检查是否有内容或附件
    if (!content && attachedFiles.length === 0) {
        showMessage('请输入消息内容或上传文件', 'error');
        return;
    }
    
    try {
        // 构建FormData
        const formData = new FormData();
        formData.append('message', content);
        
        // 添加附件（作为虚拟文件）
        attachedFiles.forEach((fileInfo, index) => {
            const blob = new Blob([fileInfo.content], { type: 'text/plain' });
            formData.append('files', blob, fileInfo.name);
        });
        
        // 发送请求
        const response = await fetch(`/api/requirements/sessions/${currentSessionId}/messages`, {
            method: 'POST',
            body: formData  // 不设置Content-Type，让浏览器自动设置
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            // 清空输入和附件
            messageInput.value = '';
            attachedFiles = [];
            updateAttachmentList();
            
            // 显示消息（现有逻辑）
            displayMessage('user', content, result.data.user_message);
            if (result.data.ai_message) {
                displayMessage('ai', result.data.ai_message.content, result.data.ai_message);
            }
        } else {
            showMessage('发送失败：' + result.message, 'error');
        }
        
    } catch (error) {
        console.error('发送消息失败:', error);
        showMessage('发送失败，请重试', 'error');
    }
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    setupFileUpload();
    // ... 其他现有初始化代码
});
```

### 4. HTML结构修改

在现有的输入框区域添加文件上传元素：

```html path=/Users/huian@thoughtworks.com/Program/intent-test-framework/web_gui/templates/requirements_analyzer.html start=null
<!-- 在消息输入区域修改 -->
<div class="input-area">
    <!-- 附件列表 -->
    <div id="attachmentList" class="attachment-list" style="display: none;"></div>
    
    <!-- 现有的消息输入框 -->
    <textarea id="messageInput" placeholder="描述您的项目需求..." rows="3"></textarea>
    
    <!-- 工具栏 -->
    <div class="input-toolbar">
        <!-- 现有的发送按钮 -->
        <button id="sendButton" onclick="sendMessage()">
            <i>📨</i> 发送
        </button>
        
        <!-- 新增：文件上传按钮 -->
        <button id="uploadBtn" class="upload-btn">
            <i>📎</i> 附件
        </button>
    </div>
    
    <!-- 隐藏的文件输入 -->
    <input type="file" id="fileInput" multiple accept=".txt,.md" style="display: none;">
</div>
```

### 5. CSS样式

```css path=/Users/huian@thoughtworks.com/Program/intent-test-framework/web_gui/static/css/requirements-analyzer.css start=null
/* 文件上传相关样式 */
.attachment-list {
    padding: 10px;
    background: #f8f9fa;
    border-radius: 6px;
    margin-bottom: 10px;
}

.attachment-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    background: white;
    border-radius: 4px;
    margin-bottom: 4px;
}

.attachment-item:last-child {
    margin-bottom: 0;
}

.attachment-icon {
    font-size: 14px;
}

.attachment-name {
    flex: 1;
    font-size: 14px;
    color: #333;
}

.attachment-size {
    font-size: 12px;
    color: #666;
}

.remove-attachment {
    background: none;
    border: none;
    color: #999;
    font-size: 16px;
    cursor: pointer;
    padding: 0 4px;
    line-height: 1;
}

.remove-attachment:hover {
    color: #ff4444;
}

.upload-btn {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    padding: 8px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.upload-btn:hover {
    background: #e9ecef;
}

.input-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
}

/* 拖拽效果 */
#messageInput.drag-over {
    border: 2px dashed #007bff;
    background: #f8f9ff;
}

/* 在消息中显示附件 */
.message-attachments {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #eee;
    font-size: 12px;
    color: #666;
}

.message-attachments .attachment-indicator {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-right: 12px;
}
```

## 实施计划

### 阶段一：后端支持（1天）
- [ ] 修改 `RequirementsMessage` 模型添加 `attached_files` 字段
- [ ] 编写数据库迁移脚本
- [ ] 修改消息发送API支持文件上传
- [ ] 添加文件处理函数（验证、读取、格式化）

### 阶段二：前端实现（1天）
- [ ] 修改 HTML 添加文件上传元素
- [ ] 实现文件选择和拖拽上传
- [ ] 实现附件列表显示和管理
- [ ] 修改消息发送逻辑支持文件
- [ ] 添加CSS样式

### 阶段三：测试和优化（0.5天）
- [ ] 测试各种文件格式和大小
- [ ] 测试错误处理和用户反馈
- [ ] 优化用户体验细节

**总计：2.5天**

## 核心优势

1. **最小化修改**：只需要一个数据库字段，复用现有API结构
2. **无文件存储**：文件内容直接存储在消息中，无需文件系统管理
3. **零配置**：不需要额外的存储服务或配置
4. **完全集成**：文件内容自动传递给AI，无需修改AI服务
5. **轻量级**：实现简单，维护成本低

这个方案既满足了文件上传需求，又最大化利用了现有架构，是最务实的选择！
