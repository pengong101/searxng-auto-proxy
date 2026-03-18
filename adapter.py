#!/usr/bin/env python3
"""
SearXNG Adaptive Proxy Detector v3.0
Automatically detect proxy availability and switch search engines
Author: pengong101
License: MIT
"""

import requests
import yaml
import subprocess
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import json
import time

# Configuration / 配置
CLASH_HOST = os.environ.get("CLASH_HOST", "localhost")
CLASH_PORT = os.environ.get("CLASH_PORT", "7890")
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8081")
SEARXNG_CONTAINER = os.environ.get("SEARXNG_CONTAINER", "searxng")
LOG_FILE = os.environ.get("LOG_FILE", "/var/log/searxng-proxy-check.log")
CONFIG_FILE = os.environ.get("CONFIG_FILE", "/etc/searxng/settings.yml")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "3600"))  # 1 hour

PROXY_URL = f"http://{CLASH_HOST}:{CLASH_PORT}"

@dataclass
class ProxyStatus:
    """Proxy status data structure"""
    available: bool
    latency_ms: float
    tested_at: str
    error: Optional[str] = None

@dataclass
class EngineStatus:
    """Search engine status"""
    name: str
    enabled: bool
    category: str  # 'global' or 'cn'
    last_tested: str
    response_time_ms: float
    error: Optional[str] = None

class SearXNGProxyAdapter:
    """SearXNG adaptive proxy adapter v3.0"""
    
    def __init__(self, 
                 clash_host: str = CLASH_HOST,
                 clash_port: str = CLASH_PORT,
                 searxng_url: str = SEARXNG_URL,
                 log_file: str = LOG_FILE):
        """
        Initialize adapter
        
        Args:
            clash_host: Clash proxy host
            clash_port: Clash proxy port
            searxng_url: SearXNG URL
            log_file: Log file path
        """
        self.clash_host = clash_host
        self.clash_port = clash_port
        self.searxng_url = searxng_url
        self.log_file = log_file
        self.proxy_url = f"http://{clash_host}:{clash_port}"
        
        # Search engine categories
        self.global_engines = ['google', 'duckduckgo', 'wikipedia', 'brave', 'startpage']
        self.cn_engines = ['baidu', 'bing']
        
        # Status cache
        self.proxy_status: Optional[ProxyStatus] = None
        self.engine_statuses: Dict[str, EngineStatus] = {}
        self.last_check: Optional[datetime] = None
    
    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'a') as f:
                f.write(log_line + '\n')
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")
    
    def check_proxy(self) -> ProxyStatus:
        """
        Check proxy availability
        
        Returns:
            ProxyStatus object
        """
        self.log("🔍 Checking Clash proxy availability...")
        
        start_time = time.time()
        
        try:
            proxies = {
                'http': self.proxy_url,
                'https': self.proxy_url
            }
            
            # Test with Google
            response = requests.get(
                'https://www.google.com',
                proxies=proxies,
                timeout=5
            )
            
            latency = (time.time() - start_time) * 1000
            
            status = ProxyStatus(
                available=True,
                latency_ms=latency,
                tested_at=datetime.now().isoformat()
            )
            
            self.log(f"✅ Proxy available (latency: {latency:.0f}ms)")
            
        except requests.exceptions.Timeout:
            status = ProxyStatus(
                available=False,
                latency_ms=0,
                tested_at=datetime.now().isoformat(),
                error="Timeout"
            )
            self.log("❌ Proxy timeout")
            
        except requests.exceptions.ConnectionError:
            status = ProxyStatus(
                available=False,
                latency_ms=0,
                tested_at=datetime.now().isoformat(),
                error="Connection failed"
            )
            self.log("❌ Proxy connection failed")
            
        except Exception as e:
            status = ProxyStatus(
                available=False,
                latency_ms=0,
                tested_at=datetime.now().isoformat(),
                error=str(e)
            )
            self.log(f"❌ Proxy error: {e}")
        
        self.proxy_status = status
        return status
    
    def test_engine(self, engine: str) -> EngineStatus:
        """
        Test single search engine
        
        Args:
            engine: Engine name
            
        Returns:
            EngineStatus object
        """
        start_time = time.time()
        
        try:
            params = {
                'q': 'test',
                'format': 'json',
                'engines': engine
            }
            
            response = requests.get(
                f"{self.searxng_url}/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            results_count = len(data.get('results', []))
            latency = (time.time() - start_time) * 1000
            
            # Determine category
            category = 'global' if engine in self.global_engines else 'cn'
            
            status = EngineStatus(
                name=engine,
                enabled=results_count > 0,
                category=category,
                last_tested=datetime.now().isoformat(),
                response_time_ms=latency
            )
            
            if results_count > 0:
                self.log(f"✅ Engine '{engine}' working ({results_count} results, {latency:.0f}ms)")
            else:
                self.log(f"⚠️ Engine '{engine}' returned no results")
            
        except Exception as e:
            status = EngineStatus(
                name=engine,
                enabled=False,
                category='global' if engine in self.global_engines else 'cn',
                last_tested=datetime.now().isoformat(),
                response_time_ms=0,
                error=str(e)
            )
            self.log(f"❌ Engine '{engine}' error: {e}")
        
        self.engine_statuses[engine] = status
        return status
    
    def update_searxng_config(self):
        """Update SearXNG configuration based on proxy status"""
        self.log("📝 Updating SearXNG configuration...")
        
        try:
            # Load current config
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = yaml.safe_load(f)
            else:
                config = {'engines': []}
            
            # Determine which engines to enable
            proxy_available = self.proxy_status and self.proxy_status.available
            
            enabled_engines = []
            disabled_engines = []
            
            for engine, status in self.engine_statuses.items():
                if status.enabled:
                    enabled_engines.append(engine)
                else:
                    disabled_engines.append(engine)
            
            self.log(f"  Enabled engines: {', '.join(enabled_engines)}")
            self.log(f"  Disabled engines: {', '.join(disabled_engines)}")
            
            # Update config
            if 'engines' not in config:
                config['engines'] = []
            
            for engine_name in self.global_engines + self.cn_engines:
                status = self.engine_statuses.get(engine_name)
                if status:
                    # Find or create engine config
                    engine_config = None
                    for eng in config['engines']:
                        if eng.get('name') == engine_name:
                            engine_config = eng
                            break
                    
                    if not engine_config:
                        engine_config = {'name': engine_name}
                        config['engines'].append(engine_config)
                    
                    engine_config['disabled'] = not status.enabled
            
            # Save config
            with open(CONFIG_FILE, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            self.log("✅ Configuration updated")
            
            # Restart SearXNG
            self.restart_searxng()
            
        except Exception as e:
            self.log(f"❌ Configuration update failed: {e}")
    
    def restart_searxng(self):
        """Restart SearXNG container"""
        self.log("🔄 Restarting SearXNG container...")
        
        try:
            subprocess.run(
                ['docker', 'restart', SEARXNG_CONTAINER],
                capture_output=True,
                timeout=30
            )
            self.log("✅ SearXNG restarted")
            time.sleep(5)  # Wait for startup
        except Exception as e:
            self.log(f"❌ Failed to restart SearXNG: {e}")
    
    def run_check(self):
        """Run full proxy and engine check"""
        self.log("=" * 60)
        self.log("🚀 Starting SearXNG proxy check")
        self.log("=" * 60)
        
        # Check proxy
        proxy_status = self.check_proxy()
        
        # Test all engines
        all_engines = self.global_engines + self.cn_engines
        for engine in all_engines:
            self.test_engine(engine)
            time.sleep(0.5)  # Rate limiting
        
        # Update configuration
        self.update_searxng_config()
        
        # Save status
        self.save_status()
        
        self.log("=" * 60)
        self.log("✅ Proxy check completed")
        self.log("=" * 60)
        
        self.last_check = datetime.now()
    
    def save_status(self):
        """Save current status to file"""
        status_file = self.log_file.replace('.log', '_status.json')
        
        status = {
            'proxy': asdict(self.proxy_status) if self.proxy_status else None,
            'engines': {k: asdict(v) for k, v in self.engine_statuses.items()},
            'last_check': self.last_check.isoformat() if self.last_check else None
        }
        
        try:
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            self.log(f"Warning: Could not save status: {e}")
    
    def should_check(self) -> bool:
        """Check if it's time to run proxy check"""
        if not self.last_check:
            return True
        
        elapsed = datetime.now() - self.last_check
        return elapsed.total_seconds() >= CHECK_INTERVAL


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SearXNG adaptive proxy detector')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--check-interval', type=int, default=CHECK_INTERVAL, 
                       help=f'Check interval in seconds (default: {CHECK_INTERVAL})')
    args = parser.parse_args()
    
    adapter = SearXNGProxyAdapter()
    
    if args.once:
        adapter.run_check()
    else:
        # Continuous monitoring
        adapter.log(f"📍 Starting continuous monitoring (interval: {args.check_interval}s)")
        
        while True:
            try:
                if adapter.should_check():
                    adapter.run_check()
                else:
                    adapter.log("⏳ Waiting for next check...")
                
                time.sleep(60)  # Check every minute if it's time
                
            except KeyboardInterrupt:
                adapter.log("👋 Stopping...")
                break
            except Exception as e:
                adapter.log(f"❌ Error: {e}")
                time.sleep(60)


if __name__ == '__main__':
    main()
