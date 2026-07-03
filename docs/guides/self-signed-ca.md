# Trusting the claude-tap self-signed CA

`claude-tap` creates a local self-signed certificate authority (CA) when HTTPS capture is used in `forward` or `web_proxy` mode. Trust this CA only on machines or containers where you want `claude-tap` to decrypt HTTPS traffic.

## Locate or generate the CA

Start a forward or web proxy once, or run the trust helper:

```bash
claude-tap --tap-proxy-mode web_proxy --tap-no-launch
# or, on macOS only:
claude-tap trust-ca
```

The public CA certificate is written to:

```text
~/.claude-tap/ca.crt
```

The private key is next to it as `~/.claude-tap/ca-key.pem`. Do not import, copy, commit, or share `ca-key.pem`.

## Windows

### Current user

1. Press `Win + R`, run `certmgr.msc`.
2. Open **Trusted Root Certification Authorities** > **Certificates**.
3. Right-click **Certificates**, choose **All Tasks** > **Import**.
4. Import `%USERPROFILE%\.claude-tap\ca.crt`.
5. Place it in **Trusted Root Certification Authorities**.
6. Restart browsers, terminals, IDEs, or clients that should use the new trust setting.

PowerShell alternative:

```powershell
Import-Certificate -FilePath "$env:USERPROFILE\.claude-tap\ca.crt" -CertStoreLocation Cert:\CurrentUser\Root
```

### Local machine

Run PowerShell as Administrator:

```powershell
Import-Certificate -FilePath "$env:USERPROFILE\.claude-tap\ca.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

## Linux

Copy the certificate into the system trust anchors and refresh the CA store.

### Debian, Ubuntu, and derivatives

```bash
sudo cp ~/.claude-tap/ca.crt /usr/local/share/ca-certificates/claude-tap.crt
sudo update-ca-certificates
```

### Fedora, RHEL, CentOS, and derivatives

```bash
sudo cp ~/.claude-tap/ca.crt /etc/pki/ca-trust/source/anchors/claude-tap.crt
sudo update-ca-trust extract
```

Restart applications after updating the trust store. Some tools use their own CA bundle; set `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `NODE_EXTRA_CA_CERTS`, or the tool-specific option when needed.

## macOS

Use the built-in helper to trust the CA in the current user's login keychain:

```bash
claude-tap trust-ca
```

Manual GUI alternative:

1. Open **Keychain Access**.
2. Select the **login** keychain.
3. Drag `~/.claude-tap/ca.crt` into the keychain.
4. Open the imported certificate, expand **Trust**, and set **Secure Sockets Layer (SSL)** to **Always Trust**.
5. Close the dialog and enter your password if prompted.

Manual CLI alternative:

```bash
security add-trusted-cert -r trustRoot -p ssl -k ~/Library/Keychains/login.keychain-db ~/.claude-tap/ca.crt
```

## Docker and container images

Containers have separate trust stores. Copy `ca.crt` into the image or mount it at runtime, then refresh the CA store inside the container.

### Debian or Ubuntu based images

```dockerfile
COPY ca.crt /usr/local/share/ca-certificates/claude-tap.crt
RUN update-ca-certificates
```

### Alpine based images

```dockerfile
RUN apk add --no-cache ca-certificates
COPY ca.crt /usr/local/share/ca-certificates/claude-tap.crt
RUN update-ca-certificates
```

### Fedora, RHEL, or UBI based images

```dockerfile
COPY ca.crt /etc/pki/ca-trust/source/anchors/claude-tap.crt
RUN update-ca-trust extract
```

Runtime mount example for Debian or Ubuntu based containers:

```bash
docker run --rm \
  -v "$HOME/.claude-tap/ca.crt:/usr/local/share/ca-certificates/claude-tap.crt:ro" \
  your-image \
  sh -lc 'update-ca-certificates && exec your-command'
```

For Node.js containers, you can also pass the certificate directly:

```bash
docker run --rm \
  -v "$HOME/.claude-tap/ca.crt:/certs/claude-tap.crt:ro" \
  -e NODE_EXTRA_CA_CERTS=/certs/claude-tap.crt \
  your-node-image
```

## Remove the CA

Remove the `claude-tap` certificate from the same trust store where you installed it, then restart affected applications. Removing trust does not delete local trace files or the files under `~/.claude-tap/`.
