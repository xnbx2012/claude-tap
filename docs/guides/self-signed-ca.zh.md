# 信任 claude-tap 自签名 CA

`claude-tap` 在 `forward` 或 `web_proxy` 模式抓取 HTTPS 时，会创建本地自签名证书颁发机构（CA）。只应在你希望 `claude-tap` 解密 HTTPS 流量的机器或容器里信任这个 CA。

## 定位或生成 CA

先启动一次 forward 或 web proxy，或运行信任辅助命令：

```bash
claude-tap --tap-proxy-mode web_proxy --tap-no-launch
# 或者，仅 macOS 支持：
claude-tap trust-ca
```

公开 CA 证书会写入：

```text
~/.claude-tap/ca.crt
```

私钥位于同一目录，文件名为 `~/.claude-tap/ca-key.pem`。不要导入、复制、提交或分享 `ca-key.pem`。

## Windows

### 当前用户

1. 按 `Win + R`，运行 `certmgr.msc`。
2. 打开 **Trusted Root Certification Authorities** > **Certificates**。
3. 右键 **Certificates**，选择 **All Tasks** > **Import**。
4. 导入 `%USERPROFILE%\.claude-tap\ca.crt`。
5. 将证书放入 **Trusted Root Certification Authorities**。
6. 重启需要使用新信任设置的浏览器、终端、IDE 或客户端。

PowerShell 替代方式：

```powershell
Import-Certificate -FilePath "$env:USERPROFILE\.claude-tap\ca.crt" -CertStoreLocation Cert:\CurrentUser\Root
```

### 本机所有用户

以管理员身份运行 PowerShell：

```powershell
Import-Certificate -FilePath "$env:USERPROFILE\.claude-tap\ca.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

## Linux

把证书复制到系统信任锚点目录，然后刷新 CA store。

### Debian、Ubuntu 及其衍生版

```bash
sudo cp ~/.claude-tap/ca.crt /usr/local/share/ca-certificates/claude-tap.crt
sudo update-ca-certificates
```

### Fedora、RHEL、CentOS 及其衍生版

```bash
sudo cp ~/.claude-tap/ca.crt /etc/pki/ca-trust/source/anchors/claude-tap.crt
sudo update-ca-trust extract
```

更新信任库后重启应用。部分工具使用自己的 CA bundle；必要时设置 `SSL_CERT_FILE`、`REQUESTS_CA_BUNDLE`、`NODE_EXTRA_CA_CERTS` 或工具专用选项。

## macOS

使用内置辅助命令，把 CA 信任到当前用户的 login keychain：

```bash
claude-tap trust-ca
```

手动 GUI 替代方式：

1. 打开 **Keychain Access**。
2. 选择 **login** keychain。
3. 把 `~/.claude-tap/ca.crt` 拖入 keychain。
4. 打开导入的证书，展开 **Trust**，将 **Secure Sockets Layer (SSL)** 设为 **Always Trust**。
5. 关闭对话框，并在提示时输入密码。

手动 CLI 替代方式：

```bash
security add-trusted-cert -r trustRoot -p ssl -k ~/Library/Keychains/login.keychain-db ~/.claude-tap/ca.crt
```

## Docker 和容器镜像

容器拥有独立的信任库。把 `ca.crt` 复制进镜像，或在运行时挂载它，然后在容器内刷新 CA store。

### Debian 或 Ubuntu 基础镜像

```dockerfile
COPY ca.crt /usr/local/share/ca-certificates/claude-tap.crt
RUN update-ca-certificates
```

### Alpine 基础镜像

```dockerfile
RUN apk add --no-cache ca-certificates
COPY ca.crt /usr/local/share/ca-certificates/claude-tap.crt
RUN update-ca-certificates
```

### Fedora、RHEL 或 UBI 基础镜像

```dockerfile
COPY ca.crt /etc/pki/ca-trust/source/anchors/claude-tap.crt
RUN update-ca-trust extract
```

Debian 或 Ubuntu 基础容器的运行时挂载示例：

```bash
docker run --rm \
  -v "$HOME/.claude-tap/ca.crt:/usr/local/share/ca-certificates/claude-tap.crt:ro" \
  your-image \
  sh -lc 'update-ca-certificates && exec your-command'
```

对于 Node.js 容器，也可以直接传入证书：

```bash
docker run --rm \
  -v "$HOME/.claude-tap/ca.crt:/certs/claude-tap.crt:ro" \
  -e NODE_EXTRA_CA_CERTS=/certs/claude-tap.crt \
  your-node-image
```

## 移除 CA

从安装时使用的同一个信任库里删除 `claude-tap` 证书，然后重启受影响的应用。取消信任不会删除本地 trace 文件，也不会删除 `~/.claude-tap/` 下的文件。
