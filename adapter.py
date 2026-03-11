#!/usr/bin/env python3
"""
SearXNG 自适应代理配置脚本
功能：检测代理可用性，自动启用/禁用全球搜索引擎
"""

import requests
import yaml
import subprocess
import sys
from datetime import datetime

# 配置 / Configuration
# 使用环境变量，支持自定义配置 / Use environment variables for custom configuration
CLASH_HOST = os.environ.get("CLASH_HOST", "localhost")  # 默认 localhost / Default to localhost
CLASH_PORT = os.environ.get("CLASH_PORT", "7890")
SEARXNG_CONTAINER = os.environ.get("SEARXNG_CONTAINER", "searxng")
LOG_FILE = os.environ.get("LOG_FILE", "/var/log/searxng-proxy-check.log")
PROXY_URL = f"http://{CLASH_HOST}:{CLASH_PORT}"

# 搜索引擎分类
GLOBAL_ENGINES = ['google', 'duckduckgo', 'wikipedia', 'brave', 'startpage']
CN_ENGINES = ['baidu', 'bing']

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_line + '\n')
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")

def check_proxy():
    """检测代理可用性"""
    log("🔍 检测 Clash 代理可用性...")
    
    try:
        proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
        response = requests.get(
            'https://www.google.com',
            proxies=proxies,
            timeout=5
        )
        log("✅ 代理可用，可以访问全球搜索引擎")
        return True
    except Exception as e:
        log(f"❌ 代理不可用：{str(e)}")
        return False

def update_searxng_config(enable_global):
    """更新 SearXNG 配置"""
    if enable_global:
        log("🌐 启用全球搜索引擎（Google, DuckDuckGo, Wikipedia...）")
    else:
        log("🇨🇳 禁用全球搜索引擎，仅保留国内引擎")
    
    # 在容器内执行 Python 脚本
    python_script = f"""
import yaml

with open('/etc/searxng/settings.yml', 'r') as f:
    config = yaml.safe_load(f)

for engine in config.get('engines', []):
    engine_name = engine.get('name')
    if engine_name in {GLOBAL_ENGINES}:
        engine['disabled'] = not {str(enable_global).lower()}
        status = "✅ 启用" if engine['disabled'] == False else "⚠️  禁用"
        print(f"{status}: {{engine_name}}")

with open('/etc/searxng/settings.yml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print("✅ 配置已更新")
"""
    
    try:
        subprocess.run(
            ['docker', 'exec', SEARXNG_CONTAINER, 'python3', '-c', python_script],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        log(f"❌ 更新配置失败：{e.stderr}")
        return False
    
    return True

def restart_searxng():
    """重启 SearXNG"""
    log("🔄 重启 SearXNG 容器...")
    
    try:
        subprocess.run(['docker', 'restart', SEARXNG_CONTAINER], check=True)
        log("⏳ 等待 SearXNG 启动...")
        import time
        time.sleep(10)  # 等待 SearXNG 完全启动
        log("✅ SearXNG 已重启")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ 重启失败：{e}")
        return False

def test_search():
    """测试搜索功能"""
    log("🧪 测试搜索功能...")
    
    import time
    time.sleep(5)  # 等待 SearXNG 完全就绪
    
    # 测试 Google（如果启用）
    try:
        response = requests.get(
            f'http://{CLASH_HOST}:{CLASH_PORT}/search?q=test&format=json&engines=google',
            timeout=15
        )
        data = response.json()
        if data.get('number_of_results', 0) > 0:
            log("✅ Google 搜索正常")
        else:
            log("⚠️  Google 搜索无结果（可能未启用）")
    except Exception as e:
        log(f"⚠️  Google 测试失败：{str(e)}")
    
    # 测试百度
    try:
        response = requests.get(
            f'http://{CLASH_HOST}:{CLASH_PORT}/search?q=test&format=json&engines=baidu',
            timeout=15
        )
        data = response.json()
        if data.get('number_of_results', 0) > 0:
            log("✅ 百度搜索正常")
        else:
            log("⚠️  百度搜索无结果")
    except Exception as e:
        log(f"⚠️  百度测试失败：{str(e)}")

def main():
    """主流程"""
    log("=" * 60)
    log("🚀 SearXNG 自适应代理检测启动")
    log("=" * 60)
    
    # 检测代理
    proxy_available = check_proxy()
    
    # 更新配置
    if not update_searxng_config(proxy_available):
        log("❌ 配置更新失败，退出")
        sys.exit(1)
    
    # 重启 SearXNG
    if not restart_searxng():
        log("❌ 重启失败，退出")
        sys.exit(1)
    
    # 测试搜索
    test_search()
    
    log("=" * 60)
    log("✅ 自适应代理检测完成")
    log("=" * 60)
    
    # 返回状态
    if proxy_available:
        log("🌐 当前状态：全球搜索引擎已启用")
    else:
        log("🇨🇳 当前状态：仅国内搜索引擎")

if __name__ == '__main__':
    main()
