# ⚙️ 后端架构设计

## 服务架构分层
```
Presentation Layer (API Routes)
├── /api/v1/testcases/          # 测试用例CRUD
├── /api/v1/variables/          # 变量管理API  
├── /api/v1/execution/          # 执行控制API
├── /api/v1/validation/         # 参数验证API
└── /api/v1/suggestions/        # 智能提示API

Business Logic Layer (Services)
├── TestCaseService             # 测试用例业务逻辑
├── VariableResolverService     # 变量解析服务
├── ExecutionContextService    # 执行上下文管理
├── ValidationService          # 参数验证服务
└── SuggestionService          # 智能提示服务

Data Access Layer (Repositories)
├── TestCaseRepository          # 测试用例数据访问
├── ExecutionHistoryRepository  # 执行历史数据访问
├── VariableRepository          # 变量数据访问
└── TemplateRepository          # 模板数据访问
```

## 核心服务设计

### 1. VariableResolverService
**职责**: 解析和替换步骤参数中的变量引用

```python
class VariableResolverService:
    def __init__(self, execution_context: ExecutionContext):
        self.execution_context = execution_context
        self.variable_pattern = re.compile(r'\$\{([^}]+)\}')
    
    def resolve_step_parameters(self, step: Step) -> Step:
        """解析步骤参数中的所有变量引用"""
        resolved_params = {}
        
        for key, value in step.params.items():
            if isinstance(value, str):
                resolved_params[key] = self._resolve_string_value(value)
            else:
                resolved_params[key] = value
        
        return Step(
            action=step.action,
            params=resolved_params,
            description=step.description
        )
    
    def _resolve_string_value(self, text: str) -> str:
        """解析字符串中的变量引用"""
        def replace_variable(match):
            variable_path = match.group(1)
            return self._get_variable_value(variable_path)
        
        return self.variable_pattern.sub(replace_variable, text)
    
    def _get_variable_value(self, variable_path: str) -> str:
        """根据变量路径获取变量值"""
        path_parts = variable_path.split('.')
        variable_name = path_parts[0]
        
        variable_data = self.execution_context.get_variable(variable_name)
        if not variable_data:
            raise VariableNotFoundError(f"Variable '{variable_name}' not found")
        
        # 支持嵌套属性访问
        current_value = variable_data.value
        for property_name in path_parts[1:]:
            if isinstance(current_value, dict) and property_name in current_value:
                current_value = current_value[property_name]
            else:
                raise VariablePropertyError(
                    f"Property '{property_name}' not found in variable '{variable_name}'"
                )
        
        return str(current_value)
```

### 2. ExecutionContextService
**职责**: 管理测试执行过程中的变量上下文

```python
class ExecutionContextService:
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.variables: Dict[str, VariableData] = {}
        self.redis_client = get_redis_client()  # 可选的Redis缓存
    
    def store_variable(self, 
                      variable_name: str, 
                      value: Any, 
                      data_type: DataType,
                      source_step: int) -> None:
        """存储步骤输出变量"""
        variable_data = VariableData(
            name=variable_name,
            value=value,
            data_type=data_type,
            source_step=source_step,
            created_at=datetime.utcnow()
        )
        
        # 内存存储
        self.variables[variable_name] = variable_data
        
        # 数据库持久化
        self._persist_variable(variable_data)
        
        # 可选的Redis缓存
        if self.redis_client:
            self._cache_variable(variable_data)
    
    def get_variable(self, variable_name: str) -> Optional[VariableData]:
        """获取变量数据"""
        # 优先从内存获取
        if variable_name in self.variables:
            return self.variables[variable_name]
        
        # 从缓存获取
        if self.redis_client:
            cached_data = self._get_cached_variable(variable_name)
            if cached_data:
                return cached_data
        
        # 从数据库获取
        return self._load_variable_from_db(variable_name)
    
    def get_all_variables(self) -> List[VariableData]:
        """获取所有可用变量"""
        return list(self.variables.values())
    
    def validate_variable_references(self, text: str) -> List[ValidationError]:
        """验证文本中的变量引用是否有效"""
        errors = []
        variable_pattern = re.compile(r'\$\{([^}]+)\}')
        
        for match in variable_pattern.finditer(text):
            variable_path = match.group(1)
            try:
                self._validate_variable_path(variable_path)
            except VariableError as e:
                errors.append(ValidationError(
                    message=str(e),
                    position=match.span(),
                    variable_path=variable_path
                ))
        
        return errors
```

### 3. ValidationService
**职责**: 参数验证和错误处理

```python
class ValidationService:
    def __init__(self):
        self.action_definitions = load_action_definitions()
    
    def validate_step(self, step: Step, available_variables: List[str]) -> ValidationResult:
        """验证步骤配置"""
        errors = []
        warnings = []
        
        # 验证Action类型
        if step.action not in self.action_definitions:
            errors.append(f"Unknown action type: {step.action}")
            return ValidationResult(errors=errors, warnings=warnings)
        
        action_def = self.action_definitions[step.action]
        
        # 验证必需参数
        for required_param in action_def.required_params:
            if required_param not in step.params:
                errors.append(f"Missing required parameter: {required_param}")
        
        # 验证参数类型和格式
        for param_name, param_value in step.params.items():
            param_template = action_def.param_templates.get(param_name)
            if param_template:
                param_errors = self._validate_parameter(
                    param_name, param_value, param_template, available_variables
                )
                errors.extend(param_errors)
        
        return ValidationResult(errors=errors, warnings=warnings)
    
    def _validate_parameter(self, 
                           param_name: str,
                           param_value: Any,
                           param_template: ParameterTemplate,
                           available_variables: List[str]) -> List[str]:
        """验证单个参数"""
        errors = []
        
        # 类型验证
        if param_template.type == ParameterType.STRING:
            if not isinstance(param_value, str):
                errors.append(f"Parameter '{param_name}' must be a string")
        
        # 变量引用验证
        if param_template.support_variables and isinstance(param_value, str):
            variable_errors = self._validate_variable_references(
                param_value, available_variables
            )
            errors.extend(variable_errors)
        
        # 自定义验证规则
        for validation_rule in param_template.validation_rules:
            rule_errors = self._apply_validation_rule(param_value, validation_rule)
            errors.extend(rule_errors)
        
        return errors
```

## API设计规范

### RESTful API结构
```python