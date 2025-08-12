# 🎨 前端架构设计

## 组件架构层次
```
App Level
├── TestCaseEditor (Container)
│   ├── StepList (Presentation)
│   │   ├── StepItem (Smart Component)
│   │   │   ├── StepParameterForm (Smart Component)
│   │   │   │   ├── SmartVariableInput (Interactive)
│   │   │   │   │   └── VariableSuggestionDropdown
│   │   │   │   ├── ParameterField (Adaptive)
│   │   │   │   └── ValidationMessage (Pure)
│   │   │   └── OutputConfiguration (Feature Component)
│   │   └── AddStepButton (Action)
│   └── VariableBrowser (Context Display)
└── ExecutionMonitor (Container)
    ├── VariableViewer (Data Display)
    └── DataFlowVisualizer (Advanced Feature)
```

## 核心前端组件设计

### 1. SmartVariableInput 组件
**职责**: 提供IDE级别的变量引用智能提示

**技术规格**:
```typescript
interface SmartVariableInputProps {
  value: string;
  onChange: (value: string) => void;
  availableVariables: Variable[];
  placeholder?: string;
  disabled?: boolean;
  validationErrors?: string[];
}

interface Variable {
  name: string;
  type: DataType;
  sourceStep: number;
  description: string;
  preview?: any;
  lastUpdated?: Date;
}

enum DataType {
  STRING = 'string',
  NUMBER = 'number', 
  BOOLEAN = 'boolean',
  OBJECT = 'object',
  ARRAY = 'array'
}
```

**核心功能实现**:
- 实时语法检测：正则表达式 `/\$\{([^}]*)/g` 检测变量引用
- 智能过滤：Fuse.js库实现模糊搜索
- 键盘导航：方向键选择，Enter确认，ESC取消
- 实时预览：显示变量当前值和类型信息

### 2. StepParameterForm 组件
**职责**: 根据Action定义动态生成参数配置表单

**动态表单生成策略**:
```typescript
interface ActionDefinition {
  id: string;
  displayName: string;
  icon: string;
  category: ActionCategory;
  requiredParams: string[];
  optionalParams: string[];
  paramTemplates: Record<string, ParameterTemplate>;
}

interface ParameterTemplate {
  type: ParameterType;
  placeholder: string;
  validation: ValidationRule[];
  supportVariables: boolean;
  defaultValue?: any;
  options?: SelectOption[];
}

enum ParameterType {
  STRING = 'string',
  NUMBER = 'number',
  BOOLEAN = 'boolean',
  SELECT = 'select',
  TEXTAREA = 'textarea',
  VARIABLE_NAME = 'variable_name',
  JSON_SCHEMA = 'json_schema'
}
```

### 3. VariableSuggestionDropdown 组件
**职责**: 显示变量提示列表，支持键盘和鼠标交互

**UI设计规范**:
- **变量分组**: 按数据类型和来源步骤分组显示
- **视觉层次**: 使用颜色编码区分不同数据类型
- **信息密度**: 显示变量名、类型、来源、预览值
- **交互反馈**: 悬停高亮、选中状态、加载状态

## 状态管理架构

### Context API 状态分层
```typescript
// 全局应用状态
interface AppContextState {
  user: User;
  settings: AppSettings;
  theme: Theme;
}

// 测试用例编辑状态
interface TestCaseEditorState {
  testCase: TestCase;
  steps: Step[];
  availableVariables: Variable[];
  validationErrors: Record<string, string[]>;
  isDirty: boolean;
}

// 执行监控状态
interface ExecutionMonitorState {
  currentExecution: ExecutionHistory;
  executionContext: ExecutionContext;
  variableValues: Record<string, any>;
  stepStatus: StepExecutionStatus[];
}
```

### 状态更新模式
- **Reducer模式**: 复杂状态变更使用useReducer管理
- **Optimistic UI**: 用户操作立即反映UI变化，后台同步
- **错误边界**: 组件级错误处理和用户友好的错误显示

## 性能优化策略

### 渲染优化
- **React.memo**: 纯组件避免不必要重渲染
- **useMemo/useCallback**: 昂贵计算和函数缓存
- **虚拟化列表**: 大量步骤列表使用react-window
- **代码分割**: 动态导入非核心功能组件

### 网络优化
- **SWR缓存**: 变量数据使用SWR实现缓存和重新验证
- **防抖处理**: 智能提示搜索使用300ms防抖
- **批量请求**: 多个变量查询合并为单个请求

---
