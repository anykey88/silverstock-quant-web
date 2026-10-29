#!/usr/bin/env bash
# ============================================================================
# Vercel 构建脚本：若环境内没有 Flutter，自动下载稳定版 SDK 后构建 Web 产物
# ----------------------------------------------------------------------------
# - 产物目录：build/web（在 vercel.json 的 outputDirectory 指定）
# - 必须使用 --web-renderer html：iPad 上首屏更快、中文字体渲染更稳
# - 首次构建会下载约 700MB 的 Flutter SDK，建议在 Vercel 项目设置里打开
#   「Build Cache」，后续构建会快很多
# ============================================================================
set -euo pipefail

FLUTTER_VERSION="3.0.0"
FLUTTER_HOME="${HOME}/flutter"

if [ ! -x "${FLUTTER_HOME}/bin/flutter" ]; then
  echo "==> 未检测到 Flutter，开始下载 ${FLUTTER_VERSION}"
  ARCHIVE="flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
  URL="https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/${ARCHIVE}"
  curl -fL --retry 3 -o "/tmp/${ARCHIVE}" "${URL}"
  tar -xf "/tmp/${ARCHIVE}" -C "${HOME}"
  rm -f "/tmp/${ARCHIVE}"
fi

export PATH="${FLUTTER_HOME}/bin:${PATH}"
export FLUTTER_SUPPRESS_ANALYTICS=true
export CI=true

flutter --no-version-check --version
flutter --no-version-check config --enable-web
flutter --no-version-check pub get
flutter --no-version-check build web --release --web-renderer html --base-href /

echo "==> 构建完成：build/web"
du -sh build/web
