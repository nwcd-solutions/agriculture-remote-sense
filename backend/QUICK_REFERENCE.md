# Backend 快速参考

## 📁 文件位置速查

| 功能 | 旧位置 | 新位置 |
|------|--------|--------|
| 查询处理器 | `lambda_query.py` | `lambda_handlers/query_handler.py` |
| 处理任务处理器 | `lambda_process.py` | `lambda_handlers/process_handler.py` |
| AOI 处理器 | `lambda_aoi.py` | `lambda_handlers/aoi_handler.py` |
| CORS 工具 | 每个文件中 | `common/security.py` |
| 输入验证 | `lambda_query.py` | `common/validators.py` |

## 🔧 常用导入

### 安全工具

```python
from common.security import (
    get_cors_headers,      # CORS 头
    sanitize_log_data,     # 日志脱敏
    safe_error_response    # 安全错误响应
)
```

### 验证器

```python
from common.validators import (
    validate_date_range,   # 日期范围验证
    validate_bbox,         # 边界框验证
    validate_limit,        # 查询限制验证
    validate_file_size,    # 文件大小验证
    validate_aoi_area      # AOI 面积验证
)
```

## 💡 代码示例

### 创建新的 Lambda 处理器

```python
import json
import os
import sys
import logging

# 导入共享模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common.security import get_cors_headers, safe_error_response
from common.validators import validate_bbox

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))


def handler(event, context):
    """Lambda 函数处理器"""
    try:
        # 1. 解析请求
        body = json.loads(event.get('body', '{}'))
        
        # 2. 验证输入
        bbox = body.get('bbox')
        is_valid, error_msg = validate_bbox(bbox)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': error_msg})
            }
        
        # 3. 处理逻辑
        result = process_data(bbox)
        
        # 4. 返回响应
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result)
        }
        
    except Exception as e:
        return safe_error_response(e)
```

### 使用验证器

```python
# 日期范围验证
is_valid, error_msg = validate_date_range('2024-01-01', '2024-12-31')
if not is_valid:
    return error_response(error_msg)

# 边界框验证
is_valid, error_msg = validate_bbox([116, 39, 117, 40])
if not is_valid:
    return error_response(error_msg)

# 文件大小验证
is_valid, error_msg = validate_file_size(file_content, max_size_mb=10)
if not is_valid:
    return error_response(error_msg)
```

### 日志脱敏

```python
from common.security import sanitize_log_data

# 原始数据
request_data = {
    'username': 'user@example.com',
    'password': 'secret123',
    'api_key': 'abc123',
    'bbox': [116, 39, 117, 40]
}

# 脱敏后记录
logger.info(f"Request: {sanitize_log_data(request_data)}")
# 输出: Request: {'username': 'user@example.com', 'password': '***REDACTED***', 
#                 'api_key': '***REDACTED***', 'bbox': [116, 39, 117, 40]}
```

## 🧪 测试命令

```bash
# 测试所有
pytest

# 测试特定模块
pytest tests/test_validators.py
pytest tests/test_security.py

# 测试 Lambda 处理器
pytest tests/test_query_api.py
pytest tests/test_process_api.py
pytest tests/test_aoi_api.py

# 测试覆盖率
pytest --cov=backend --cov-report=html
```

## 🚀 部署命令

```bash
# 开发环境
cd infrastructure
cdk deploy --all

# 生产环境
export CORS_ORIGINS=https://yourdomain.com
export ENVIRONMENT=prod
cdk deploy --all --context environment=prod
```

## 🔍 调试技巧

### 本地测试 Lambda 函数

```python
# test_local.py
from lambda_handlers.query_handler import handler

event = {
    'httpMethod': 'POST',
    'path': '/api/query',
    'body': json.dumps({
        'satellite': 'sentinel-2',
        'bbox': [116, 39, 117, 40],
        'start_date': '2024-01-01',
        'end_date': '2024-12-31'
    })
}

response = handler(event, None)
print(json.dumps(response, indent=2))
```

### 查看日志

```bash
# CloudWatch Logs
aws logs tail /aws/lambda/satellite-gis-query-dev --follow

# 本地日志
tail -f backend/logs/app.log
```

## 📊 验证规则速查

| 验证项 | 规则 | 错误信息 |
|--------|------|----------|
| 日期范围 | 最大 5 年 | "Date range too large (maximum 5 years)" |
| 边界框大小 | 最大 10° x 10° | "Bounding box too large (maximum 10° x 10°)" |
| 经度范围 | -180 到 180 | "Longitude must be between -180 and 180" |
| 纬度范围 | -90 到 90 | "Latitude must be between -90 and 90" |
| 查询限制 | 1 到 100 | "limit must be between 1 and 100" |
| 文件大小 | 最大 10MB | "File size exceeds maximum allowed size of 10MB" |
| AOI 面积 | 最大 100,000 km² | "AOI area exceeds maximum allowed area" |

## 🔐 安全检查清单

- [ ] 使用 `get_cors_headers()` 而不是硬编码
- [ ] 使用 `sanitize_log_data()` 记录敏感数据
- [ ] 使用 `safe_error_response()` 处理错误
- [ ] 验证所有用户输入
- [ ] 不在日志中记录密码、token、key
- [ ] 生产环境设置 `CORS_ORIGINS`
- [ ] 生产环境设置 `ENVIRONMENT=prod`

## 🐛 常见问题

### Q: 导入错误 "No module named 'common'"

```python
# 解决方案：添加路径
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from common.security import get_cors_headers
```

### Q: Lambda 函数找不到处理器

```bash
# 确保兼容层文件存在
ls backend/lambda_query.py
ls backend/lambda_process.py
ls backend/lambda_aoi.py
```

### Q: 测试失败

```bash
# 确保安装了所有依赖
pip install -r requirements.txt

# 确保 PYTHONPATH 正确
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
pytest
```

## 📞 获取帮助

- 查看 `backend/README.md` 获取详细文档
- 查看 `BACKEND_REFACTORING.md` 了解重构详情
- 查看测试用例获取使用示例
- 提交 Issue 报告问题

---

**最后更新**: 2026-02-08  
**版本**: 2.0
