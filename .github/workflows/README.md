# GitHub Actions 自动构建 Docker 镜像

## 📋 配置步骤

### 1️⃣ 配置 Docker Hub 密钥

在 GitHub 仓库中配置 Docker Hub 的凭证：

1. 进入仓库的 **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**
3. 添加以下两个密钥：

| Secret Name | Secret Value | 说明 |
|------------|--------------|------|
| `DOCKER_USERNAME` | `awdress` | 你的 Docker Hub 用户名 |
| `DOCKER_PASSWORD` | `你的访问令牌` | Docker Hub 访问令牌 |

#### 🔑 获取 Docker Hub 访问令牌

1. 登录 [Docker Hub](https://hub.docker.com/)
2. 点击右上角头像 → **Account Settings**
3. 选择 **Security** → **New Access Token**
4. 输入描述（如：GitHub Actions）
5. 权限选择：**Read, Write, Delete**
6. 点击 **Generate** 并复制生成的令牌

### 2️⃣ 触发构建

工作流会在以下情况自动触发：

- ✅ **推送到 main 分支**：自动构建并推送 `latest` 标签
- ✅ **创建版本标签**：如 `v4.2.0`，自动构建并推送对应版本
- ✅ **Pull Request**：仅构建测试，不推送
- ✅ **手动触发**：在 Actions 页面手动运行

### 3️⃣ 手动触发构建

1. 进入仓库的 **Actions** 页面
2. 选择 **Build and Push Docker Image** 工作流
3. 点击 **Run workflow** 按钮
4. 选择分支，点击 **Run workflow**

### 4️⃣ 创建版本标签（推荐）

推送带版本号的标签以触发版本构建：

```bash
# 创建并推送版本标签
git tag -a v4.2.0 -m "Release v4.2.0"
git push origin v4.2.0
```

这将自动构建并推送以下标签的镜像：
- `awdress/awembypush:v4.2.0`
- `awdress/awembypush:4.2`
- `awdress/awembypush:4`
- `awdress/awembypush:latest`

## 🏗️ 构建说明

### 支持的平台

- ✅ `linux/amd64` (x86_64)
- ✅ `linux/arm64` (aarch64)

### 构建缓存

- 使用 GitHub Actions Cache 加速构建
- 自动缓存层以提高后续构建速度

### 构建时间

- 首次构建：约 3-5 分钟
- 后续构建：约 1-2 分钟（得益于缓存）

## 📊 查看构建状态

在仓库的 **Actions** 页面可以查看：
- ✅ 构建进度
- ✅ 构建日志
- ✅ 推送的镜像标签

## 🚀 使用构建的镜像

构建完成后，可以直接拉取使用：

```bash
# 拉取最新版本
docker pull awdress/awembypush:latest

# 拉取指定版本
docker pull awdress/awembypush:v4.2.0

# 拉取 ARM64 版本（多架构镜像会自动选择）
docker pull awdress/awembypush:latest
```

## 🔧 自定义配置

如需修改构建配置，编辑 `.github/workflows/docker-build.yml` 文件：

- 修改支持的平台
- 调整标签策略
- 添加构建参数
- 配置通知等

## ⚠️ 注意事项

1. **首次配置**：确保已正确设置 Docker Hub 密钥
2. **权限检查**：确保 GitHub Actions 有仓库写入权限
3. **Docker Hub 限制**：免费账户有拉取限制，建议升级或使用缓存
4. **多架构构建**：需要更多构建时间，但提供更好的兼容性

