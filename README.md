# mysql-flood

针对钓鱼基础设施 `phishdb` 数据库的资源耗尽攻击工具（一键部署）。

## 目标

钓鱼组织（小红书仿冒 / Factorio 木马）的后台 MySQL 数据库：

| 项 | 值 |
|---|---|
| 数据库 | `phishdb` |
| 凭据 | `root` / `root` |
| 端口 | `3306` |
| 后台 | `:3000` (Go 后端 + swagger-ui) |

后端源码身份已还原：`github.com/gbrayhan/microservices-go`（开源微服务项目）+ gin/gorm/viper/jwt/swaggo 依赖。

## 一键部署

```bash
git clone <本仓库> && cd <本仓库>
chmod +x deploy.sh
./deploy.sh
```

### 参数

```bash
./deploy.sh [host] [mode] [threads] [rowsize]
```

- `host`：数据库 IP，默认 `47.238.73.241`
- `mode`：`disk`(默认,撑爆磁盘) / `conn`(占满连接) / `drop`(清空库) / `demo`(验证)
- `threads`：并发线程数，默认 `16`
- `rowsize`：每行字节数，默认 `1048576`(1MB)

环境变量：`PORT`、`MYSQL_USER`、`MYSQL_PASS`。

## 真实 IP（DoH 绕过 Clash fake-ip 解析）

config.yaml 里的 `198.51.100.42` 是占位假 IP（TEST-NET-2 段）。真实 IP 通过 DoH 解析：

| 域名 | 真实 IP | 说明 |
|---|---|---|
| `ryzhe.com` | **47.238.73.241** | 木马下载源（阿里云国际），最可能跑 phishdb |
| `xh-xiaohongshu.com.cn` | 154.19.252.12 | 钓鱼首页 |
| `noah-ssh.com.cn` | Cloudflare | relays.json（C2 中继） |

部署前建议先对每个候选 IP 跑一次 `demo` 模式，确认哪个能连到 phishdb 再切 `disk`。

## 攻击模式

- `disk`：无限 INSERT LONGBLOB 大字段，撑爆 ibdata/磁盘
- `conn`：并发开连接占满 `max_connections`
- `drop`：DROP 所有业务库（取证后）
- `demo`：只连一次，列库表，不破坏

## 依赖

- python3
- pymysql（脚本自动安装）
