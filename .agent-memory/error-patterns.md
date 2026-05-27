# 错误模式库
# 格式: [错误签名] → [根因] → [修复方案]

## 路径编码错误
### 错误签名: UnicodeEncodeError
### 根因: 反斜杠 \U \T 被当作转义序列
### 修复: 用正斜杠 C:/Users/... 或 raw string
### 预防: Python 脚本中路径一律用正斜杠

## npm 超时
### 错误签名: npm install 超时
### 根因: 默认 registry 网络慢
### 修复: --registry=https://registry.npmmirror.com
### 预防: 安装命令自动加镜像参数

## 变量持久化丢失
### 错误签名: 上一命令定义的变量下一命令不可用
### 根因: PowerShell 每个命令块独立作用域
### 修复: 在同一命令块中完成读取和写入
### 预防: 将相关操作合并到同一命令块

## OOXML 注释不渲染
### 根因: LibreOffice 不支持渲染注释
### 修复: 结构性检查（检查 XML 结构）
### 预防: 涉及注释时直接检查 OOXML

## python-docx 路径问题
### 根因: 路径含反斜杠 + Unicode
### 修复: os.path.join 或正斜杠
### 预防: 始终用 os.path.join
