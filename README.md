# HTTP Test Server for Embedded Clients

用于测试嵌入式HTTP客户端的特殊响应服务器。

## 快速开始

```bash
python server.py -c config/routes.json -H 0.0.0.0 -p 8080
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c, --config` | 配置文件路径 | config/routes.json |
| `-H, --host` | 绑定地址 | 0.0.0.0 |
| `-p, --port` | 监听端口 | 8080 |
| `-l, --log-level` | 日志级别 | INFO |

## 特殊响应类型

### 网络层响应

| ID | 路径 | 说明 |
|----|------|------|
| R002 | /ignore-connection-close | 忽略Connection: close,响应后保持连接30秒 |
| R003 | /timeout-before-response | 响应前等待60秒 |
| R005 | /slow-chunked | 分块传输,每块延迟0.5秒 |
| R006 | /drop-after-bytes | 发送50字节后断开 |
| R007 | /drop-after-time | 5秒后断开不响应 |
| R008 | /partial-response | 仅发送15字节后断开 |

### 协议层响应

| ID | 路径 | 说明 |
|----|------|------|
| R004 | /duplicate-content-length | 多个Content-Length头 |
| R009 | /no-content-length | 无Content-Length头 |
| R010 | /wrong-content-length | Content-Length与实际不符 |
| R013 | /http10 | HTTP/1.0响应 |
| R016 | /invalid-header | 包含非法字符的响应头 |
| R017 | /no-status-line | 无状态行响应 |
| R018 | /missing-header-end | 缺少头部结束符 |

### 功能层响应

| ID | 路径 | 说明 |
|----|------|------|
| R001 | /normal | 正常200响应 |
| R011 | /large-response | 10MB大响应 |
| R019 | /redirect | 302重定向 |
| R020 | /auth/basic | Basic认证挑战 |

## 配置示例

```json
{
    "id": "R002",
    "path": "/ignore-connection-close",
    "methods": ["GET", "POST"],
    "handler_type": "ignore_connection_close",
    "timeout": 30,
    "body": "Response sent, connection held",
    "description": "Ignores Connection: close header"
}
```

### 配置字段

| 字段 | 说明 |
|------|------|
| id | 路由编号 |
| path | URL路径,支持{param}参数 |
| methods | 允许的HTTP方法 |
| handler_type | 特殊处理器类型 |
| type | 响应类型(normal/malformed/chunked/large/slow) |
| status | HTTP状态码 |
| headers | 响应头 |
| body | 响应体 |
| timeout | 超时时间(秒) |
| chunk_delay | 分块延迟(秒) |
| drop_after_bytes | N字节后断开 |
| drop_after_time | N秒后断开 |