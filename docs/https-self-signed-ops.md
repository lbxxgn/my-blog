# 自签 HTTPS（IP 访问）运维手册

> 适用场景：服务器只有公网 IP、没有域名（或域名被 ICP 备案拦截），但需要 HTTPS
> 才能使用 PWA / Service Worker / Passkey 等安全上下文能力。
>
> 本文基于一次真实故障的排查沉淀（2026-09，服务器 OpenSSL 1.1.1k FIPS，IP `47.106.255.91`）。

---

## 1. 基本概念（先看这个，避免踩坑）

自签 HTTPS 涉及**两张不同的证书**，很多人在这里搞混：

| 证书 | 文件 | 作用 | 装到哪里 |
| --- | --- | --- | --- |
| 根 CA | `ca.pem` / `ca.crt` | 你自己签发的“信任锚” | **客户端**（iPhone/Mac 等）装这个并设为完全信任 |
| 服务器证书 | `server.pem` | 由 CA 签发给这个 IP 的叶子证书 | **服务器** nginx 使用，不要装到客户端 |

- 客户端**只装 CA**。信任了 CA，就等于信任它签发的所有服务器证书。
- 服务器证书是叶子证书（`CA:FALSE`），**不能**作为信任根，装了也没用。
- 命令行看到的“序列号”和浏览器看到的“序列号”不一样是正常的：一个看的是 CA，一个是叶子证书。要对比请**同类比同类**，且优先比 SHA-256 指纹而不是序列号。

链路关系：

```
my-blog Local CA (ca.pem)   ← 客户端信任这个
      └── server.pem (CN=服务器IP)   ← nginx 使用
```

---

## 2. 一次性生成（推荐用法）

> ⚠️ 关键原则：**CA 和服务器证书必须在同一次顺序执行中生成**，中间不要中断，
> 否则会出现“issuer 对不上”的验证失败。
>
> ⚠️ **不要为了同一个服务反复重跑本流程**：每重跑一次 CA 就变了，所有设备都要重装 CA。
> 证书有效期够长（CA 10 年、服务器 397 天），到期只需重签服务器证书。

### 2.1 用 openssl.cnf（兼容性最好）

> 不要用 `openssl req -x509 -addext ...` 的方式：在 OpenSSL 1.1.1k（FIPS）上会出现
> CA 自验证失败（`unable to get local issuer certificate`）。用配置文件最稳。

把 `IP` 换成你的服务器公网 IP：

```bash
CERT_DIR=/etc/ssl/my-blog
IP=47.106.255.91
mkdir -p "$CERT_DIR" && cd "$CERT_DIR"

cat > "$CERT_DIR/openssl.cnf" <<CONF
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[ dn ]
CN = my-blog Local CA

[ v3_ca ]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash

[ v3_server ]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[ alt_names ]
IP.1 = $IP
IP.2 = 127.0.0.1
DNS.1 = localhost
CONF

# 1) 根 CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -key ca.key -sha256 -days 3650 \
  -out ca.pem -config "$CERT_DIR/openssl.cnf" -extensions v3_ca

# 2) 服务器证书（有效期 <= 825 天，Apple 对 TLS 服务器证书有上限）
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=$IP" -config "$CERT_DIR/openssl.cnf"
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
  -out server.pem -days 397 -sha256 \
  -extfile "$CERT_DIR/openssl.cnf" -extensions v3_server

# 3) nginx 用的链证书 + 客户端用的 DER
cat server.pem ca.pem > server-fullchain.pem
openssl x509 -in ca.pem -outform der -out ca.crt

# 4) 权限与清理
chmod 600 ca.key server.key
chmod 644 ca.pem server.pem server-fullchain.pem ca.crt openssl.cnf
rm -f server.csr ca.srl
```

### 2.2 生成后必须验证

```bash
cd /etc/ssl/my-blog
openssl verify -CAfile ca.pem ca.pem       # 必须 ca.pem: OK
openssl verify -CAfile ca.pem server.pem   # 必须 server.pem: OK
openssl x509 -in ca.pem -noout -subject -fingerprint -sha256   # 记下 CA 指纹，装客户端时核对
openssl x509 -in server.pem -noout -issuer -dates              # issuer 应等于 CA 的 subject
```

只有出现两行 `OK` 才继续。

### 2.3 nginx 配置

`nginx-ssl-selfsigned.conf.example` 中的证书路径（默认 `/etc/ssl/my-blog/...`）：

```nginx
ssl_certificate     /etc/ssl/my-blog/server-fullchain.pem;
ssl_certificate_key /etc/ssl/my-blog/server.key;
```

应用并确认：

```bash
nginx -T 2>/dev/null | grep ssl_certificate   # 确认路径就是上面两个
nginx -t && systemctl reload nginx
```

确认线上实际发出的证书已更新：

```bash
echo | openssl s_client -connect 127.0.0.1:443 -servername <IP> 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

---

## 3. 客户端安装 CA

### 3.1 iPhone / iPad

**方式 A：配置描述文件（推荐）**

```bash
# 服务器上：生成内嵌 CA 的 .mobileconfig
cd <项目根目录>
sudo CERT_DIR=/etc/ssl/my-blog ./scripts/make-apple-cert-profile.sh
sudo cp /etc/ssl/my-blog/my-blog-ca.mobileconfig static/
sudo chmod 644 static/my-blog-ca.mobileconfig
```

iPhone Safari 打开 `https://<IP>/static/my-blog-ca.mobileconfig`：

1. 会先弹“非私人连接”警告 → 「显示详细信息」→「访问此网站」（只是下载文件）。
2. 安装描述文件，输锁屏密码。
3. **关键**：设置 → 通用 → 关于本机 → 证书信任设置 → 打开 `my-blog Local CA` 的「完全信任」。
4. 彻底关掉 Safari 再重新打开。

**方式 B：直接安装 `ca.crt`**：把 `ca.crt` 通过 AirDrop/邮件发到 iPhone，点开安装，再到「证书信任设置」开启完全信任。

> 删除旧证书：设置 → 通用 → VPN与设备管理，删除旧的 `my-blog CA` 描述文件。

### 3.2 Mac

```bash
# 1) 取 CA（scp 或从站点下载）
scp root@<IP>:/etc/ssl/my-blog/ca.crt ~/Downloads/my-blog-ca.crt

# 2) 加入系统钥匙串并设为信任根（系统级）
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain ~/Downloads/my-blog-ca.crt

# 3) 验证
curl -v https://<IP>/ 2>&1 | grep -E "subject:|issuer:|SSL certificate verify"
# 出现 SSL certificate verify ok 即成功
```

图形界面替代方案：双击 `ca.crt` → 加入「系统」钥匙串 → 找到 `my-blog Local CA` →
双击 → 「信任」→「使用此证书时」选 **始终信任**。

Safari / Chrome 使用系统钥匙串，加完即生效；若仍警告，彻底退出浏览器再开。
也需核对钥匙串里 CA 的 SHA-256 指纹与服务器输出一致。

### 3.3 Windows / Android（备查）

- **Windows**：双击 `ca.crt` → 安装证书 → 本地计算机 → 「受信任的根证书颁发机构」。
- **Android**：设置 → 安全 → 加密与凭据 → 安装证书 → CA 证书，选 `ca.crt`。

---

## 4. 常见报错与定位

### 4.1 `FetchEvent.respondWith received an error: TypeError: Load failed`（Safari）

- **原因**：旧版 Service Worker 在 `fetch` 里对所有请求 `event.respondWith(fetch(event.request))`
  且无 catch，任一请求失败（证书未信任/断网/中断）就会让 Promise reject。
- **代码修复**：`static/sw.js` 改为空 `fetch` 监听，不调用 `respondWith`（已修复，勿回退）。
- **设备侧**：旧 SW 会一直驻留，需清除网站数据或卸载 PWA 后重装。
- 注意：本错误也常是**证书不受信任**的表现，修证书后一并消失。

### 4.2 `此连接非私人连接`（已安装并信任 CA 仍报）

按顺序排查：

1. **CA 是否合规**：必须有 `Basic Constraints: critical, CA:TRUE`；
   `openssl verify -CAfile ca.pem ca.pem` 必须 OK。
2. **装的是不是当前 CA**：对比 iPhone 里 CA 指纹与服务器 `ca.pem` 的 SHA-256。
3. **服务器证书有效期**：超过 Apple 上限（825 天，脚本曾用 3650 天）会被直接拒绝。改为 ≤ 397 天。
4. **完全信任开关**：设置 → 通用 → 关于本机 → 证书信任设置，必须打开。
5. **访问地址与 SAN 不一致**：证书 SAN 里的 IP 必须与你访问用的一致（不要混用域名/内网 IP）。
6. iPhone 会缓存证书校验失败结果：彻底关闭 Safari，必要时重启手机。

### 4.3 `openssl verify` 报 `unable to get local issuer certificate`（error 20）

含义：**`server.pem` 的 issuer 在 `ca.pem` 里找不到** —— 两者不是同一批生成的。

- 先确认 `pwd` 是 `/etc/ssl/my-blog`，用**绝对路径**验证，别在项目目录里对着旧副本验证。
- 对比 `server.pem` 的 `issuer` 与 `ca.pem` 的 `subject`，必须一致。
- 若 CA 自验证（`verify -CAfile ca.pem ca.pem`）都失败，说明 CA 不正：多半是用了
  `openssl req -x509 -addext ...` 且版本兼容问题，改用本文第 2.1 节的 `openssl.cnf` 方式重做。
- 最稳妥的修复：删掉旧产物、**在同一次执行内**按 §2.1 重新生成 CA 和 server。

### 4.4 浏览器看到的序列号与命令行不一致

正常现象：浏览器默认显示**叶子（服务器）证书**，命令行可能查的是 **CA**。
对比时用同一张证书的 **SHA-256 指纹**，不要用序列号（显示进制也可能不同）。

---

## 5. 与仓库脚本的关系

- `scripts/setup-https-selfsigned.sh`：一键生成自签 CA + 服务器证书。
  - 已按本文 §2 改造：使用 `openssl.cnf`（`[v3_ca]`/`[v3_server]`）生成，服务器证书默认 397 天，
    默认复用已有 CA（`FORCE_CA=1` 强制更换），生成后自动 `openssl verify` 自检并打印 CA 指纹。
  - 日常续期只需重跑本脚本（会复用 CA，只重签服务器证书），客户端无需重装 CA。
- `scripts/make-apple-cert-profile.sh`：把当前 `ca.pem` 打成 iPhone 用的 `.mobileconfig`（内嵌 CA，方向正确）。
- `nginx-ssl-selfsigned.conf.example`：IP + 自签的 nginx 配置模板。
- `scripts/cleanup-https-sslip.sh`：清理 sslip.io / Let's Encrypt 方案残留。

> 待办建议：把 `setup-https-selfsigned.sh` 改为本文的 `openssl.cnf` 方式，服务器证书有效期改为 397 天，
> 并加入“CA 已存在则复用、避免重复生成”。

---

## 6. 速查清单

```bash
# 生成并验证
bash <按 §2.1 执行> && \
  openssl verify -CAfile /etc/ssl/my-blog/ca.pem /etc/ssl/my-blog/server.pem

# 生效
nginx -t && systemctl reload nginx

# CA 指纹（客户端核对）
openssl x509 -in /etc/ssl/my-blog/ca.pem -noout -fingerprint -sha256

# iPhone 描述文件
sudo CERT_DIR=/etc/ssl/my-blog ./scripts/make-apple-cert-profile.sh && \
  sudo cp /etc/ssl/my-blog/my-blog-ca.mobileconfig static/

# Mac 信任根
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain ~/Downloads/my-blog-ca.crt
```
