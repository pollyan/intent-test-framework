# 智能助手文件上传功能实施计划（最终版）

## 项目概述

### 目标
为智能需求分析助手系统添加文件上传功能，支持用户上传txt和md格式的文档文件，将文件内容作为对话背景信息直接传递给AI助手。

### 核心价值
- **增强上下文理解**：基于上传文档内容提供更准确的需求分析
- **提升工作效率**：避免用户手动输入大量文档内容  
- **简洁易用**：专注于txt和md两种常用文档格式
- **原文传递**：保持文档内容的完整性，无额外处理

### 功能范围
✅ **包含功能**：
- 点击上传：通过上传按钮选择本地文件
- 拖拽上传：直接拖拽文件到输入框区域
- 格式限制：仅支持`.txt`和`.md`文件
- 上传进度：实时显示上传进度和状态
- 附件预览：上传前显示文件列表，支持移除
- 消息集成：文件作为消息的一部分显示
- 原文传递：将文件内容直接加入AI对话上下文

❌ **不包含功能**：
- 其他文件格式支持（doc、pdf等）
- 智能文档解析和摘要
- 文件内容向量化
- 文件版本管理
- 云存储集成

## 技术架构设计

### 前端架构

#### 组件设计
```
FileUploadSystem/
├── UploadButton/              # 上传按钮组件
│   ├── 文件选择触发
│   ├── 格式验证
│   └── 视觉反馈
├── DragDropZone/              # 拖拽上传区域  
│   ├── 拖拽事件处理
│   ├── 拖拽视觉反馈
│   └── 格式验证
├── FilePreview/               # 附件预览组件
│   ├── 附件列表显示
│   ├── 文件信息展示
│   └── 移除操作
├── UploadProgress/            # 上传进度组件
│   ├── 进度条显示
│   ├── 状态更新
│   └── 完成处理
└── MessageAttachment/         # 消息中的附件显示
    ├── 文件图标
    ├── 文件名称
    └── 文件大小
```

#### 状态管理
```javascript
const FileUploadState = {
    attachedFiles: [],           // 当前附件列表
    uploadingFiles: [],          // 上传中的文件
    maxFileSize: 10 * 1024 * 1024,  // 10MB
    maxTotalSize: 50 * 1024 * 1024, // 50MB
    allowedFormats: ['.txt', '.md'], // 仅支持两种格式
    dragCounter: 0               // 拖拽计数器
};
```

### 后端架构

#### API接口设计
```python
# 文件上传API
POST /api/requirements/files/upload
Content-Type: multipart/form-data
{
    "files": [File1, File2, ...],
    "session_id": "current_session_id", 
    "message_id": "optional_message_id"
}

Response:
{
    "code": 200,
    "message": "文件上传成功",
    "data": {
        "uploaded_files": [
            {
                "file_id": "uuid",
                "filename": "requirements.md",
                "size": 1024,
                "content_type": "text/markdown",
                "text_content": "# 需求文档\n\n文档内容...",
                "upload_time": "2024-01-01T00:00:00Z"
            }
        ]
    }
}

# 文件内容获取API
GET /api/requirements/files/{file_id}/content
Response: 纯文本内容

# 文件删除API
DELETE /api/requirements/files/{file_id}

# 会话文件列表API  
GET /api/requirements/sessions/{session_id}/files
```

#### 数据库设计
```sql
-- 上传文件表
CREATE TABLE uploaded_files (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES requirements_sessions(id),
    message_id UUID REFERENCES requirements_messages(id),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_path TEXT NOT NULL,
    text_content TEXT NOT NULL,  -- 直接存储文本内容
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 消息文件关联表（多对多）
CREATE TABLE message_files (
    message_id UUID REFERENCES requirements_messages(id),
    file_id UUID REFERENCES uploaded_files(id),
    PRIMARY KEY (message_id, file_id)
);

-- 索引优化
CREATE INDEX idx_uploaded_files_session_id ON uploaded_files(session_id);
CREATE INDEX idx_uploaded_files_message_id ON uploaded_files(message_id);
CREATE INDEX idx_message_files_message_id ON message_files(message_id);
```

### 服务层设计

#### FileUploadService
```python
class FileUploadService:
    def __init__(self, storage_service, database_service):
        self.storage = storage_service
        self.db = database_service
    
    async def upload_files(self, files: List[UploadFile], session_id: str, message_id: str = None):
        """上传文件并提取内容"""
        uploaded_files = []
        
        for file in files:
            # 1. 验证文件格式和大小
            self.validate_file(file)
            
            # 2. 读取文件内容（txt/md都是纯文本）
            text_content = await self.read_text_content(file)
            
            # 3. 保存文件到存储系统
            file_path = await self.storage.save_file(file)
            
            # 4. 保存文件记录到数据库
            file_record = await self.save_file_record(
                session_id, message_id, file, file_path, text_content
            )
            
            uploaded_files.append(file_record)
            
        return uploaded_files
    
    def validate_file(self, file: UploadFile):
        """验证文件格式和大小"""
        # 检查文件扩展名
        ext = Path(file.filename).suffix.lower()
        if ext not in ['.txt', '.md']:
            raise ValidationError(f"不支持的文件格式: {ext}")
        
        # 检查文件大小
        if file.size > 10 * 1024 * 1024:  # 10MB
            raise ValidationError(f"文件过大: {file.size} bytes")
            
        return True
        
    async def read_text_content(self, file: UploadFile) -> str:
        """读取文本文件内容"""
        content = await file.read()
        # 尝试不同编码
        for encoding in ['utf-8', 'gbk', 'gb2312']:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("无法解码文件内容")
        
    async def get_files_by_session(self, session_id: str) -> List[dict]:
        """获取会话的所有文件"""
        return await self.db.get_files_by_session(session_id)
```

## 实施计划

### 第一阶段：后端基础设施（2天）

#### Day 1: 数据模型和存储
**任务清单**：
- [ ] 设计并创建数据库表结构
- [ ] 编写数据库迁移脚本
- [ ] 实现FileUploadService基础类
- [ ] 实现文件存储服务（本地存储）
- [ ] 添加文件验证逻辑

**交付物**：
- `migrations/add_file_upload_tables.sql`
- `web_gui/services/file_upload_service.py`
- `web_gui/services/file_storage_service.py`
- 基础单元测试

**验收标准**：
- 数据库表创建成功
- 文件验证逻辑正确（只接受txt和md）
- 文件存储和读取功能正常

#### Day 2: API接口实现
**任务清单**：
- [ ] 实现文件上传API端点
- [ ] 实现文件获取和删除API
- [ ] 添加错误处理和响应格式化
- [ ] 编写API测试用例

**交付物**：
- `web_gui/api/files.py`
- API测试套件
- API文档更新

**验收标准**：
- 文件上传API返回正确格式
- 错误处理完善
- API测试覆盖率 > 90%

### 第二阶段：前端上传组件（2天）

#### Day 3: 基础上传组件
**任务清单**：
- [ ] 实现文件选择按钮和隐藏input
- [ ] 添加文件格式和大小验证
- [ ] 实现附件预览列表组件
- [ ] 添加文件移除功能

**交付物**：
- 更新`requirements_analyzer.html`模板
- 文件上传JavaScript模块
- CSS样式更新

**验收标准**：
- 点击上传功能正常
- 文件格式验证生效
- 附件预览列表显示正确

#### Day 4: 拖拽上传和进度显示
**任务清单**：
- [ ] 实现拖拽上传功能
- [ ] 添加拖拽视觉反馈
- [ ] 实现上传进度显示
- [ ] 优化用户体验和错误提示

**交付物**：
- 完整的拖拽上传功能
- 上传进度显示组件
- 用户体验优化

**验收标准**：
- 拖拽上传流畅无误
- 进度显示准确
- 用户反馈清晰

### 第三阶段：AI集成和消息显示（1天）

#### Day 5: 消息集成和AI上下文
**任务清单**：
- [ ] 实现消息中的附件显示
- [ ] 将文件内容集成到AI对话上下文
- [ ] 更新消息发送逻辑
- [ ] 测试AI对文件内容的理解

**交付物**：
- 消息附件显示组件
- AI上下文集成逻辑
- 完整的端到端功能

**验收标准**：
- 附件在消息中正确显示
- AI能理解和引用文件内容
- 整个流程端到端正常

## 技术实现细节

### 前端实现要点

#### 文件验证
```javascript
function validateFile(file) {
    const allowedExtensions = ['.txt', '.md'];
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(ext)) {
        throw new Error(`不支持的文件格式: ${ext}。仅支持 txt 和 md 文件。`);
    }
    
    if (file.size > maxSize) {
        throw new Error(`文件过大: ${formatFileSize(file.size)}。最大支持 10MB。`);
    }
    
    return true;
}
```

#### 拖拽处理
```javascript
function setupDragAndDrop() {
    const dropZone = document.querySelector('.input-area');
    const dragOverlay = document.getElementById('dragOverlay');
    
    let dragCounter = 0;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    dropZone.addEventListener('dragenter', handleDragIn);
    dropZone.addEventListener('dragover', handleDragIn);
    dropZone.addEventListener('dragleave', handleDragOut);
    dropZone.addEventListener('drop', handleDrop);
    
    function handleDragIn() {
        dragCounter++;
        dragOverlay.classList.add('active');
    }
    
    function handleDragOut() {
        dragCounter--;
        if (dragCounter === 0) {
            dragOverlay.classList.remove('active');
        }
    }
    
    function handleDrop(e) {
        dragCounter = 0;
        dragOverlay.classList.remove('active');
        
        const files = Array.from(e.dataTransfer.files);
        handleFiles(files);
    }
}
```

#### 上传进度管理
```javascript
function uploadFile(file) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('files', file);
        formData.append('session_id', currentSessionId);
        
        const xhr = new XMLHttpRequest();
        
        // 进度监听
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const progress = (e.loaded / e.total) * 100;
                updateUploadProgress(file.id, progress, '上传中...');
            }
        });
        
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                resolve(response.data.uploaded_files[0]);
            } else {
                reject(new Error('上传失败'));
            }
        });
        
        xhr.addEventListener('error', () => {
            reject(new Error('网络错误'));
        });
        
        xhr.open('POST', '/api/requirements/files/upload');
        xhr.send(formData);
    });
}
```

### 后端实现要点

#### 文件上传处理
```python
@files_bp.route('/upload', methods=['POST'])
async def upload_files():
    try:
        files = request.files.getlist('files')
        session_id = request.form.get('session_id')
        message_id = request.form.get('message_id')
        
        if not files:
            return jsonify({"code": 400, "message": "没有文件"}), 400
            
        if not session_id:
            return jsonify({"code": 400, "message": "缺少会话ID"}), 400
        
        upload_service = FileUploadService()
        uploaded_files = await upload_service.upload_files(files, session_id, message_id)
        
        return jsonify({
            "code": 200,
            "message": "上传成功",
            "data": {
                "uploaded_files": uploaded_files
            }
        })
        
    except ValidationError as e:
        return jsonify({"code": 400, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return jsonify({"code": 500, "message": "上传失败"}), 500
```

#### AI上下文集成
```python
async def prepare_ai_context(message_content: str, session_id: str) -> str:
    """准备AI对话上下文，包含文件内容"""
    context_parts = []
    
    # 获取会话的文件内容
    file_service = FileUploadService()
    files = await file_service.get_files_by_session(session_id)
    
    if files:
        context_parts.append("=== 相关文档内容 ===")
        for file in files:
            context_parts.append(f"\n## 文档：{file['filename']}\n")
            context_parts.append(file['text_content'])
        context_parts.append("\n=== 用户问题 ===")
    
    context_parts.append(message_content)
    
    return "\n".join(context_parts)
```

## 测试策略

### 单元测试
**覆盖范围**：
- 文件验证逻辑
- 文件上传服务
- 文本内容读取
- 数据库操作

**测试工具**：pytest + pytest-asyncio

### 集成测试
**测试场景**：
- 文件上传完整流程
- AI上下文集成
- 错误处理流程
- 并发上传

### 端到端测试
**测试用例**：
- 点击上传txt文件
- 拖拽上传md文件
- 多文件同时上传
- 文件格式验证
- 文件大小限制
- AI基于文件内容回答

## 部署和配置

### 环境变量
```bash
# 文件存储配置
FILE_STORAGE_PATH=/app/uploads
MAX_FILE_SIZE=10485760  # 10MB in bytes
MAX_TOTAL_SIZE=52428800  # 50MB in bytes

# 支持的文件格式（逗号分隔）
ALLOWED_FILE_FORMATS=.txt,.md
```

### 目录结构
```
uploads/
├── 2024/
│   ├── 01/
│   │   ├── sessions/
│   │   │   ├── session_uuid_1/
│   │   │   │   ├── file1.txt
│   │   │   │   └── file2.md
│   │   │   └── session_uuid_2/
│   │   └── orphaned/  # 未关联会话的文件
│   └── 02/
└── temp/  # 临时文件存储
```

## 监控和运维

### 关键指标
- 上传成功率：> 99%
- 平均上传时间：< 2秒（10MB以下）
- 存储空间使用量
- 每日上传文件数量
- 文件格式分布统计

### 日志记录
```python
# 文件上传日志
logger.info(f"文件上传开始: session={session_id}, file={filename}, size={file_size}")
logger.info(f"文件上传成功: file_id={file_id}, duration={duration}ms")

# 错误日志
logger.error(f"文件上传失败: session={session_id}, file={filename}, error={error}")
logger.warning(f"文件格式被拒绝: file={filename}, ext={ext}")
```

### 清理策略
- **临时文件清理**：24小时后自动删除temp目录文件
- **孤儿文件清理**：7天后删除未关联会话的文件
- **会话文件保留**：30天后归档老会话文件
- **存储空间监控**：使用率超过80%时告警

## 性能优化

### 前端优化
- **文件读取优化**：使用FileReader API逐步读取大文件
- **进度反馈优化**：实时更新上传进度，避免用户等待焦虑
- **错误重试机制**：网络中断时自动重试上传
- **本地缓存**：已上传文件信息缓存，避免重复上传

### 后端优化
- **异步处理**：使用异步I/O处理文件读写
- **文件流处理**：大文件分块处理，避免内存占用过高
- **数据库索引**：为查询频繁的字段添加索引
- **连接池**：数据库连接池优化并发性能

## 风险评估与缓解

### 技术风险

#### 1. 文件编码问题
**风险**：用户上传的文件使用不同编码导致乱码
**缓解策略**：
- 支持常见编码格式自动检测（utf-8, gbk, gb2312）
- 提供编码格式选择选项
- 明确提示支持的编码格式

#### 2. 大文件上传超时
**风险**：大文件上传过程中网络中断或超时
**缓解策略**：
- 设置合理的文件大小限制（10MB）
- 实现断点续传功能
- 提供上传失败重试机制

### 安全风险

#### 1. 恶意文件上传
**风险**：用户上传包含恶意代码的文件
**缓解策略**：
- 严格限制文件格式（仅txt和md）
- 文件内容扫描和过滤
- 文件存储隔离，不允许执行

#### 2. 存储空间滥用
**风险**：用户恶意上传大量文件占用存储空间
**缓解策略**：
- 单文件大小限制（10MB）
- 总存储空间限制（每用户50MB）
- 实施文件清理策略

## 后续扩展计划

### Phase 2: 增强功能（未来考虑）
- [ ] 支持更多文档格式（docx, pdf）
- [ ] 文件内容搜索功能
- [ ] 文件版本管理
- [ ] 协作和分享功能

### Phase 3: 智能功能（未来考虑）
- [ ] 文档内容自动摘要
- [ ] 关键信息提取
- [ ] 文档相似度分析
- [ ] 智能标签和分类

---

## 总结

这个实施计划专注于核心需求，提供一个简单、可靠、易用的文件上传功能：

### 核心优势
1. **简洁专注**：只支持txt和md格式，避免复杂性
2. **用户友好**：点击和拖拽两种上传方式，实时进度反馈
3. **技术稳健**：基于现有架构，最小化系统影响
4. **易于维护**：清晰的代码结构和完善的测试覆盖

### 开发周期
- **总时间**：5个工作日
- **开发人员**：1名全栈开发者
- **里程碑**：每天明确的交付物和验收标准

这个方案在保证功能完整性的同时，最大化了开发效率和系统稳定性。
