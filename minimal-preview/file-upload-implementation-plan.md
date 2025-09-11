# 智能助手文件上传功能实施规划

## 项目概述

### 目标
为智能需求分析助手系统添加文件上传功能，支持用户上传需求文档、测试文件等背景资料，提升AI助手的分析准确性和上下文理解能力。

### 核心价值
- **增强上下文理解**：基于上传文档提供更准确的需求分析和测试建议
- **提升工作效率**：避免用户手动输入大量文档内容
- **支持多种格式**：覆盖常见的文档和数据格式
- **优化用户体验**：支持拖拽上传，实时进度反馈

## 功能需求分析

### 用户故事

#### 主要场景
```
作为产品经理
我想要上传现有的PRD文档到需求分析助手
以便基于现有文档进行需求澄清和完善
```

```
作为测试工程师  
我想要上传需求规格说明书到测试分析助手
以便生成针对性的测试策略和测试用例
```

#### 辅助场景
```
作为项目成员
我想要能够拖拽文件到聊天界面
以便快速上传参考文档而不中断对话流程
```

### 功能特性

#### 1. 文件上传方式
- **点击上传**：通过上传按钮选择本地文件
- **拖拽上传**：直接拖拽文件到输入框区域
- **多文件支持**：同时选择和上传多个文件
- **重复检测**：防止重复上传同名文件

#### 2. 支持的文件格式
- **文档格式**：`.txt`, `.md`, `.doc`, `.docx`, `.pdf`, `.rtf`
- **数据格式**：`.csv`, `.json`, `.yaml`, `.yml`, `.xml`
- **配置文件**：各种文本配置文件
- **大小限制**：单文件最大10MB，总计最大50MB

#### 3. 上传进度与状态
- **实时进度条**：显示上传百分比
- **状态反馈**：上传中、上传完成、上传失败
- **可取消上传**：允许用户中断上传过程
- **错误处理**：文件格式不支持、文件过大等错误提示

#### 4. 文件内容处理
- **文本提取**：从各种格式中提取纯文本内容
- **内容解析**：结构化解析文档内容
- **上下文整合**：将文件内容作为对话背景信息
- **智能总结**：对长文档进行关键信息提取

## 技术架构设计

### 前端架构

#### 组件设计
```
FileUploadSystem/
├── UploadButton/              # 上传按钮组件
│   ├── 文件选择触发
│   ├── 多文件选择
│   └── 格式验证
├── DragDropZone/              # 拖拽上传区域
│   ├── 拖拽事件处理
│   ├── 视觉反馈
│   └── 文件接收
├── FilePreview/               # 文件预览组件
│   ├── 附件列表显示
│   ├── 文件信息展示
│   └── 移除文件操作
├── UploadProgress/            # 上传进度组件
│   ├── 进度条显示
│   ├── 状态更新
│   └── 取消上传
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
    uploadQueue: [],             // 上传队列
    maxFileSize: 10 * 1024 * 1024,  // 10MB
    maxTotalSize: 50 * 1024 * 1024, // 50MB
    allowedFormats: ['.txt', '.md', '.doc', '.docx', '.pdf', '.rtf', '.csv', '.json', '.yaml', '.yml', '.xml']
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
                "filename": "requirements.docx",
                "size": 1024000,
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "extracted_text": "文档文本内容...",
                "upload_time": "2024-01-01T00:00:00Z"
            }
        ]
    }
}

# 文件内容获取API
GET /api/requirements/files/{file_id}/content
Response: 原始文本内容

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
    extracted_text TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 文件处理日志表
CREATE TABLE file_processing_logs (
    id UUID PRIMARY KEY,
    file_id UUID REFERENCES uploaded_files(id),
    processing_type VARCHAR(50), -- 'text_extraction', 'content_analysis', 'error_handling'
    status VARCHAR(20), -- 'processing', 'completed', 'failed'
    result_data JSONB,
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 消息文件关联表（多对多）
CREATE TABLE message_files (
    message_id UUID REFERENCES requirements_messages(id),
    file_id UUID REFERENCES uploaded_files(id),
    PRIMARY KEY (message_id, file_id)
);
```

### 服务层设计

#### FileUploadService
```python
class FileUploadService:
    def __init__(self, storage_service, text_extraction_service):
        self.storage = storage_service
        self.text_extractor = text_extraction_service
    
    async def upload_files(self, files: List[UploadFile], session_id: str, message_id: str = None):
        """上传文件并提取内容"""
        uploaded_files = []
        
        for file in files:
            # 1. 验证文件格式和大小
            self.validate_file(file)
            
            # 2. 保存文件到存储系统
            file_path = await self.storage.save_file(file)
            
            # 3. 提取文本内容
            extracted_text = await self.text_extractor.extract_text(file_path, file.content_type)
            
            # 4. 保存文件记录到数据库
            file_record = await self.save_file_record(
                session_id, message_id, file, file_path, extracted_text
            )
            
            uploaded_files.append(file_record)
            
        return uploaded_files
    
    def validate_file(self, file: UploadFile):
        """验证文件格式和大小"""
        # 检查文件扩展名
        # 检查文件大小
        # 检查MIME类型
        pass
        
    async def extract_and_analyze_content(self, file_id: str):
        """提取并分析文件内容"""
        # 获取文件记录
        # 提取文本内容
        # 进行内容分析和总结
        # 更新文件记录
        pass
```

#### TextExtractionService  
```python
class TextExtractionService:
    def __init__(self):
        self.extractors = {
            'text/plain': self.extract_plain_text,
            'text/markdown': self.extract_markdown,
            'application/pdf': self.extract_pdf,
            'application/msword': self.extract_doc,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self.extract_docx,
            'text/csv': self.extract_csv,
            'application/json': self.extract_json,
            'application/x-yaml': self.extract_yaml,
            'application/xml': self.extract_xml,
        }
    
    async def extract_text(self, file_path: str, content_type: str) -> str:
        """根据文件类型提取文本内容"""
        extractor = self.extractors.get(content_type)
        if not extractor:
            raise ValueError(f"不支持的文件类型: {content_type}")
        
        return await extractor(file_path)
    
    async def extract_pdf(self, file_path: str) -> str:
        """提取PDF文本内容"""
        # 使用 PyPDF2 或 pdfplumber
        pass
        
    async def extract_docx(self, file_path: str) -> str:
        """提取DOCX文本内容"""
        # 使用 python-docx
        pass
```

## 实施计划

### 第一阶段：基础文件上传（3天）

#### Day 1: 后端基础架构
- [ ] 设计数据库表结构并创建迁移脚本
- [ ] 实现文件上传API接口
- [ ] 实现基础文件验证和存储功能
- [ ] 配置文件存储系统（本地或云存储）

**交付物**：
- 数据库迁移文件
- 文件上传API（`POST /api/requirements/files/upload`）
- 基础文件存储功能
- API测试套件

#### Day 2: 文本内容提取
- [ ] 实现TextExtractionService核心逻辑
- [ ] 支持主要文件格式的文本提取（txt, md, pdf, docx）
- [ ] 实现错误处理和异常管理
- [ ] 添加文件处理日志记录

**交付物**：
- TextExtractionService完整实现
- 多格式文本提取功能
- 错误处理机制
- 单元测试覆盖率 > 85%

#### Day 3: 前端文件上传组件
- [ ] 实现文件选择和上传按钮
- [ ] 添加文件格式验证和大小检查
- [ ] 实现上传进度显示
- [ ] 集成后端上传API

**交付物**：
- 文件上传组件
- 上传进度反馈
- 错误处理和用户提示
- 前后端集成测试

### 第二阶段：拖拽上传和UI优化（2天）

#### Day 4: 拖拽上传功能
- [ ] 实现拖拽区域和事件处理
- [ ] 添加拖拽视觉反馈和状态指示
- [ ] 实现多文件拖拽支持
- [ ] 优化用户体验和交互流程

**交付物**：
- 拖拽上传功能
- 视觉反馈和状态指示
- 多文件拖拽支持
- 用户体验优化

#### Day 5: 附件显示和管理
- [ ] 实现附件预览组件
- [ ] 在消息中显示文件附件
- [ ] 添加文件移除和管理功能
- [ ] 优化附件列表和文件信息显示

**交付物**：
- 附件预览和管理界面
- 消息中的附件显示
- 文件管理操作
- UI/UX优化

### 第三阶段：AI集成和高级功能（2天）

#### Day 6: AI内容集成
- [ ] 将上传文件内容整合到AI对话上下文
- [ ] 实现文件内容的智能摘要和分析
- [ ] 优化长文档的内容处理策略
- [ ] 添加文件内容引用和回溯功能

**交付物**：
- AI对话上下文集成
- 文件内容智能分析
- 长文档处理优化
- 内容引用功能

#### Day 7: 测试和性能优化
- [ ] 端到端测试和用户验收测试
- [ ] 性能优化和内存管理
- [ ] 大文件处理和并发上传测试
- [ ] 安全性验证和漏洞扫描

**交付物**：
- 完整的E2E测试套件
- 性能优化报告
- 安全性验证报告
- 部署文档和配置

## 技术实现细节

### 文件格式支持

#### 文本格式处理
```python
# 纯文本文件
async def extract_plain_text(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# Markdown文件  
async def extract_markdown(file_path: str) -> str:
    import markdown
    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    # 可选择保留Markdown格式或转换为纯文本
    return md_content

# PDF文件
async def extract_pdf(file_path: str) -> str:
    import PyPDF2
    text = ""
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text.strip()

# Word文档
async def extract_docx(file_path: str) -> str:
    from docx import Document
    doc = Document(file_path)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text.strip()
```

#### 数据格式处理
```python
# CSV文件
async def extract_csv(file_path: str) -> str:
    import pandas as pd
    df = pd.read_csv(file_path)
    # 转换为易于理解的文本格式
    return f"CSV数据摘要：\n共{len(df)}行数据\n列名：{', '.join(df.columns)}\n前几行数据：\n{df.head().to_string()}"

# JSON文件
async def extract_json(file_path: str) -> str:
    import json
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 格式化JSON为可读文本
    return json.dumps(data, ensure_ascii=False, indent=2)

# YAML文件
async def extract_yaml(file_path: str) -> str:
    import yaml
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return yaml.dump(data, allow_unicode=True, default_flow_style=False)
```

### 文件存储策略

#### 本地存储
```python
class LocalFileStorage:
    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
    
    async def save_file(self, file: UploadFile) -> str:
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix
        filename = f"{file_id}{file_ext}"
        file_path = self.upload_dir / filename
        
        # 保存文件
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
            
        return str(file_path)
```

#### 云存储（可选）
```python
class CloudFileStorage:
    def __init__(self, bucket_name: str, access_key: str, secret_key: str):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        self.bucket_name = bucket_name
    
    async def save_file(self, file: UploadFile) -> str:
        file_id = str(uuid.uuid4())
        file_key = f"uploads/{file_id}_{file.filename}"
        
        # 上传到S3
        await self.s3_client.upload_fileobj(
            file.file, 
            self.bucket_name, 
            file_key
        )
        
        return file_key
```

### 安全性考虑

#### 文件验证
```python
class FileValidator:
    ALLOWED_EXTENSIONS = {'.txt', '.md', '.doc', '.docx', '.pdf', '.rtf', '.csv', '.json', '.yaml', '.yml', '.xml'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB
    
    def validate_file(self, file: UploadFile):
        # 1. 检查文件扩展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise ValidationError(f"不支持的文件格式: {file_ext}")
        
        # 2. 检查文件大小
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError(f"文件过大: {file.size} bytes (最大 {self.MAX_FILE_SIZE} bytes)")
        
        # 3. 检查MIME类型
        if not self.is_allowed_content_type(file.content_type):
            raise ValidationError(f"不允许的文件类型: {file.content_type}")
        
        return True
    
    def validate_total_size(self, files: List[UploadFile]):
        total_size = sum(file.size for file in files)
        if total_size > self.MAX_TOTAL_SIZE:
            raise ValidationError(f"文件总大小过大: {total_size} bytes (最大 {self.MAX_TOTAL_SIZE} bytes)")
```

#### 内容安全扫描
```python
async def scan_file_content(file_path: str) -> bool:
    """扫描文件内容是否安全"""
    # 1. 病毒扫描（如果可用）
    # 2. 恶意内容检测
    # 3. 敏感信息检测
    return True
```

## 性能优化

### 文件处理优化
- **异步处理**：文件上传和文本提取使用异步处理
- **分块上传**：大文件分块上传，提高成功率
- **缓存机制**：文件内容提取结果缓存
- **队列处理**：文件处理任务队列化

### 前端优化
- **进度反馈**：实时上传进度显示
- **错误重试**：上传失败自动重试
- **本地预览**：上传前本地文件预览
- **压缩优化**：图片和文档适当压缩

## 风险评估与缓解

### 技术风险

#### 1. 大文件处理
**风险**：大文件上传超时或内存溢出
**缓解策略**：
- 实现分块上传机制
- 设置合理的文件大小限制
- 使用流式处理避免内存问题

#### 2. 文本提取失败
**风险**：某些文件格式无法正确提取文本
**缓解策略**：
- 多种提取库备选方案
- 优雅的错误处理和降级策略
- 提供手动文本输入选项

#### 3. 安全漏洞
**风险**：恶意文件上传导致安全问题
**缓解策略**：
- 严格的文件格式和内容验证
- 文件隔离存储和处理
- 定期安全扫描和更新

### 用户体验风险

#### 1. 上传速度慢
**风险**：网络较慢时上传体验差
**缓解策略**：
- 压缩文件减小传输量
- 分块上传支持断点续传
- 清晰的进度指示和预期时间

#### 2. 文件格式不支持
**风险**：用户常用格式不在支持列表中
**缓解策略**：
- 广泛支持常见文档格式
- 清晰的格式支持说明
- 格式转换建议和工具推荐

## 测试策略

### 单元测试
- **文件上传服务**：FileUploadService各方法测试
- **文本提取服务**：各种格式的文本提取测试
- **文件验证**：格式、大小、内容验证测试
- **覆盖率目标**：> 90%

### 集成测试
- **API集成**：文件上传、获取、删除API测试
- **数据库集成**：文件记录存储和查询测试
- **AI集成**：文件内容与AI对话集成测试
- **存储集成**：本地和云存储功能测试

### 端到端测试
- **完整上传流程**：从选择文件到AI使用文件内容
- **拖拽上传**：拖拽文件到页面的完整流程
- **多文件上传**：同时上传多个文件的处理
- **错误场景**：各种异常情况的处理

### 性能测试
- **大文件上传**：10MB文件上传性能测试
- **并发上传**：多用户同时上传文件测试
- **文本提取**：各种格式文件的提取速度测试
- **内存使用**：文件处理过程中的内存占用监控

## 监控和运维

### 关键指标
- **上传成功率**：文件上传成功的百分比
- **提取成功率**：文本内容提取成功的百分比
- **平均上传时间**：不同大小文件的平均上传时间
- **存储使用量**：文件存储空间使用情况
- **用户使用频率**：文件上传功能的使用统计

### 日志记录
```python
# 文件上传日志
logger.info(f"File upload started: user={user_id}, file={filename}, size={file_size}")
logger.info(f"File upload completed: file_id={file_id}, duration={duration}ms")

# 文本提取日志
logger.info(f"Text extraction started: file_id={file_id}, type={content_type}")
logger.info(f"Text extraction completed: file_id={file_id}, text_length={text_length}")

# 错误日志
logger.error(f"File upload failed: file={filename}, error={error_msg}")
logger.error(f"Text extraction failed: file_id={file_id}, error={error_msg}")
```

### 告警机制
- **上传失败率**：超过5%时告警
- **存储空间**：使用率超过80%时告警
- **处理队列**：积压超过100个任务时告警
- **系统资源**：CPU/内存使用率异常时告警

## 后续优化方向

### 功能增强
- [ ] 支持更多文件格式（PPT, XLS等）
- [ ] 文件内容智能分类和标签
- [ ] 批量文件处理和管理
- [ ] 文件版本管理和历史记录
- [ ] 文件分享和协作功能

### 性能优化
- [ ] CDN加速文件传输
- [ ] 文件内容搜索和索引
- [ ] 智能文件压缩和优化
- [ ] 分布式文件处理
- [ ] 缓存策略优化

### AI集成优化
- [ ] 文件内容向量化和相似度匹配
- [ ] 智能文档摘要和关键信息提取
- [ ] 多文档交叉引用和关联分析
- [ ] 基于文档内容的自动问答

---

## 总结

这个文件上传功能实施规划涵盖了从需求分析到技术实现的全过程：

1. **全面的格式支持**：涵盖常见文档和数据格式
2. **优秀的用户体验**：支持拖拽上传、实时进度、直观反馈
3. **robust的技术架构**：模块化设计、异步处理、错误恢复
4. **完善的安全机制**：文件验证、内容扫描、权限控制
5. **优化的性能表现**：分块上传、缓存机制、队列处理

预计总开发时间：**7个工作日**，将显著提升智能助手的实用性和用户体验。
