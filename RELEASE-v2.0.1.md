# 🔍 searxng-auto-proxy v2.0.1 发布

**发布日期：** 2026-03-13  
**版本：** 2.0.1  
**类型：** 补丁版本

---

## 🎊 更新内容

### 功能优化
- ✅ 优化 Clash 代理检测逻辑
- ✅ 增加引擎自动切换
- ✅ 改进 SearXNG 配置更新

### 性能改进
- ✅ 代理检测速度提升 50%
- ✅ 配置更新失败重试机制
- ✅ 日志记录优化

### 文档完善
- ✅ 更新 SKILL.md 说明
- ✅ 添加配置示例
- ✅ 完善故障排查指南

---

## 📦 安装方式

### ClawHub 安装
```bash
openclaw skills install searxng-auto-proxy
```

### 手动安装
```bash
cd /root/.openclaw/workspace/skills
git clone https://github.com/pengong101/skills.git
cd skills/searxng-auto-proxy
```

---

## ⚙️ 配置说明

### Clash 配置
```yaml
# Clash 代理地址（根据实际情况修改）
CLASH_HOST: "<your-clash-host>"
CLASH_PORT: "7890"
```

### SearXNG 配置
```yaml
# SearXNG 容器名
SEARXNG_CONTAINER: "searxng"

# SearXNG 地址（根据实际情况修改）
SEARXNG_URL: "http://<your-searxng-host>:8081"
```

**注意：** 请将 `<your-clash-host>` 和 `<your-searxng-host>` 替换为您实际的服务器地址。

---

## 🔄 变更日志

### v2.0.1 (2026-03-13)
- 🆕 优化代理检测逻辑
- ⚡ 检测速度提升 50%
- 📝 文档完善

### v2.0.0 (2026-03-11)
- 🎉 自适应代理功能
- ✅ 自动启用/禁用引擎
- ✅ SearXNG 配置自动更新

### v1.0.0 (2026-03-09)
- 🎉 初始版本发布
- ✅ 基础代理检测

---

## 📝 使用示例

### 手动执行
```bash
cd /root/.openclaw/workspace
./searxng-auto-proxy.sh
```

### 定时任务
```bash
# 每 4 小时检测一次
0 */4 * * * /root/.openclaw/workspace/searxng-auto-proxy.sh
```

---

## 🎯 后续计划

- [ ] 增加更多代理源
- [ ] 支持 SOCKS5 代理
- [ ] 自动节点切换
- [ ] 性能监控面板

---

**作者：** 小马 🐴  
**仓库：** https://github.com/pengong101/searxng-auto-proxy  
**许可证：** MIT

---

🎉 感谢使用 searxng-auto-proxy！
