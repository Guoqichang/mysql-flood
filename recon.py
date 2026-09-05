#!/usr/bin/env python3
"""钓鱼基础设施侦察: DoH 解析当前真实 IP + 端口扫描 (零依赖, 纯 socket)"""
import socket, json, urllib.request, concurrent.futures, sys

DOMAINS = [
    "ryzhe.com",
    "www.ryzhe.com",
    "xh-xiaohongshu.com.cn",
    "www.xh-xiaohongshu.com.cn",
    "noah-ssh.com.cn",
]

# 重点端口: MySQL / 后台 / 常见服务
PORTS = [21, 22, 25, 53, 80, 443, 3000, 3306, 6379, 8080, 8443, 8888, 9090, 27017]

DOH_SERVERS = [
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/resolve",
]

def doh_resolve(domain):
    ips = set()
    for server in DOH_SERVERS:
        url = f"{server}?name={domain}&type=A"
        req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
        try:
            data = json.load(urllib.request.urlopen(req, timeout=10))
            for a in data.get("Answer", []):
                if a.get("type") == 1:
                    ips.add(a["data"])
        except Exception as e:
            ips.add(f"ERR({e})")
    return sorted(ips)

def scan_port(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        r = s.connect_ex((ip, port))
        if r == 0:
            banner = b""
            try:
                s.settimeout(2)
                s.send(b"\r\n")
                banner = s.recv(256)
            except Exception:
                pass
            return port, "OPEN", banner
        return port, None, None
    except Exception:
        return port, None, None
    finally:
        s.close()

def main():
    targets = set(sys.argv[1:])
    print("=" * 60)
    print(" 钓鱼基础设施侦察")
    print("=" * 60)
    for d in DOMAINS:
        print(f"\n[*] DoH 解析 {d}:")
        for ip in doh_resolve(d):
            print(f"    {ip}")
            targets.add(ip)

    for ip in sorted(t for t in targets if not t.startswith("ERR")):
        print(f"\n[*] 扫描 {ip} (端口 {PORTS})")
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            futs = {ex.submit(scan_port, ip, p): p for p in PORTS}
            for f in concurrent.futures.as_completed(futs):
                port, status, banner = f.result()
                if status == "OPEN":
                    b = banner[:50].replace(b"\r", b" ").replace(b"\n", b" ")
                    print(f"    [OPEN] {ip}:{port}  {b!r}")

if __name__ == "__main__":
    main()
