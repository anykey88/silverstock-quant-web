# Vercel 部署指引（SilverStock-Quant-Web）

本项目是 **Flutter Web 纯静态产物**（`build/web`），不需要 Node 服务端，也不需要数据库。下面给两条路线，按需要选一条即可。

- **方案 A：上传已构建产物**（1 分钟，最稳，适合比赛赶时间）
- **方案 B：连 GitHub 自动构建**（首次慢，之后每次 push 自动更新）

---

## 0. 前置：本地先构建一次

```bash
cd silverstock_quant_web
flutter pub get

# 关键参数说明：
#   --release            压缩 + tree-shaking，产物最小
#   --web-renderer html  用 HTML/CSS 渲染，iPad 首屏更快、中文字体不用额外打包
#   --base-href /        部署在域名根目录（Vercel 默认就是根目录）
flutter build web --release --web-renderer html --base-href /

# 可选：删掉用不到的 CanvasKit 运行库（HTML renderer 不需要），可省约 16MB
rm -rf build/web/canvaskit

du -sh build/web      # 约 4.4 MB
```

本地验收：

```bash
cd build/web && python3 -m http.server 8080
# 浏览器打开 http://localhost:8080 ，用 DevTools 切到 iPad mini 尺寸看版式
```

---

## 方案 A：上传构建产物（推荐比赛使用）

### A-1 命令行

```bash
npm i -g vercel          # 只需一次
cd silverstock_quant_web
vercel login
vercel deploy build/web --prod
```

终端会输出形如 `https://silverstock-quant-web.vercel.app` 的地址，即为公网 HTTPS 链接。

> `vercel deploy <目录>` 是「部署一个已构建好的静态目录」，不会执行任何构建命令，因此**不受 Vercel 没有 Flutter 环境的影响**。

### A-2 网页拖拽

1. 登录 <https://vercel.com/new>；
2. 选择 **Deploy** 页签下的拖拽区域，把 **`build/web` 文件夹整个拖进去**；
3. 等 10–30 秒，得到 `https://<随机名>.vercel.app`；
4. 进 **Settings → Domains** 可以改项目名/绑定自有域名。

### A-3 注意事项

- 一定要拖 `build/web` 这一层（里面直接是 `index.html`、`main.dart.js`、`assets/`），不要拖项目根目录。
- 上传后如果页面空白，99% 是 `--base-href` 写错了：Vercel 根目录部署必须用 `--base-href /`。

---

## 方案 B：连 GitHub 自动构建

### B-1 推仓库

```bash
cd silverstock_quant_web
git init && git add . && git commit -m "feat: SilverStock-Quant-Web 参赛版"
git branch -M main
git remote add origin https://github.com/<你的账号>/silverstock-quant-web.git
git push -u origin main
```

`.gitignore` 已排除 `build/`、`.dart_tool/`，仓库里只保留源码与数据快照。

### B-2 Vercel 导入

1. **Add New… → Project → Import Git Repository**，选中该仓库；
2. **Framework Preset** 选 `Other`；
3. **Root Directory** 保持 `./`；
4. **Build & Output Settings** 展开，填：
   - Install Command：`echo "skip npm install"`
   - Build Command：`bash scripts/vercel-build.sh`
   - Output Directory：`build/web`
5. **Deploy**。

`vercel.json` 里已经预置了同样的设置，所以第 4 步通常会自动带出来，确认一下即可。

### B-3 `scripts/vercel-build.sh` 做了什么

1. 检查 `$HOME/flutter` 是否存在，没有就下载 **Flutter 3.0.0 stable**（约 700MB，首次 3–6 分钟）；
2. `flutter pub get`；
3. `flutter build web --release --web-renderer html --base-href /`；
4. 输出 `build/web`。

**建议打开 Vercel 的 Build Cache**（项目 Settings → General → Build & Development Settings），否则每次构建都会重新下载 Flutter SDK，容易触发 45 分钟构建上限。

### B-4 想换 Flutter 版本

改 `scripts/vercel-build.sh` 第 9 行：

```bash
FLUTTER_VERSION="3.0.0"     # 改成你要的稳定版号
```

---

## 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 页面全白、控制台 404 `main.dart.js` | `--base-href` 与实际路径不一致 | 根目录部署用 `--base-href /`；子路径部署用 `--base-href /子路径/` |
| 刷新子页面 404 | 用了 Path URL Strategy | 本项目默认 hash 路由；`vercel.json` 已配置 fallback rewrite 兜底 |
| 构建超时 / 卡在下载 Flutter | 未开构建缓存 | 打开 Build Cache；或改用方案 A |
| 中文显示成方框 | 误用了 CanvasKit 渲染 | 构建命令加 `--web-renderer html` |
| 部署后还是旧版本 | 浏览器/Service Worker 缓存 | 强制刷新（Cmd/Ctrl+Shift+R）；`vercel.json` 已对 `main.dart.js` 设置 `must-revalidate` |
| 语音按钮没反应 | Safari 需要用户手势 + 麦克风授权 | 先点一下页面再点语音；在系统设置里允许麦克风 |

---

## 自定义域名（可选）

1. Vercel 项目 → **Settings → Domains → Add**；
2. 输入域名（如 `silverstock.example.tw`）；
3. 按提示到域名商添加 `A` 记录 `76.76.21.21` 或 `CNAME` `cname.vercel-dns.com`；
4. 等待 DNS 生效（通常 5–30 分钟），Vercel 自动签发 HTTPS 证书。

---

## 部署后必做的 5 项验收

- [ ] `https://<域名>/` 打开正常，顶部固定免责声明完整显示
- [ ] 点「执行回测」能跑完 5 个 Agent 并出报告
- [ ] 曲线图上有「历史回测不等于未来收益」水印
- [ ] 「存到本机」→ 刷新 → 首页「我的学习纪录」仍在
- [ ] iPad mini 竖屏 / 横屏各开一次，无横向滚动、无裁切

验收通过后，把这个链接填进活动投稿表单的「体验链接」一栏。
