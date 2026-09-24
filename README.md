# 陶艺工作室共窑排程 API

小型陶艺工作室的「共窑」排程服务：提交 1～14 件器物（唯一编号、正整数体积、允许烧成温度闭区间）与单窑容量，服务用**位掩码动态规划**求出覆盖全部器物的**最少窑次**方案，并保存方案供按 ID 读取。

- 技术栈：Python 3.11 · FastAPI · SQLite（标准库 `sqlite3`）
- 装窑约束：
  - 同窑器物**总体积 ≤ 单窑容量**；
  - 同窑器物的允许温度区间必须有**公共交集**，本窑烧成温度取**交集下界**
    （即 `max(各下界)`，此时所有器物均可烧成）。
- 平局规则：窑次数相同时，每窑编号升序排列，再将各窑按「编号序列」排序，取**整体字典序最小**的方案。
- 单件器物体积超过单窑容量时返回 **400** 及明确错误信息。

## 单条命令启动

需安装 Docker（含 Compose 插件），在项目根目录执行：

```bash
docker compose up --build -d
```

启动后 API 监听在：**http://localhost:8000**

- 接口文档（Swagger UI）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

停止与查看日志：

```bash
docker compose down          # 停止（数据保留在卷 kiln-data 中）
docker compose logs -f       # 查看日志
```

> 容器启动时会自动执行：① 安装 Python 依赖（`entrypoint.sh` 中 `pip install`）；
> ② 初始化 SQLite 数据库（幂等建表）；③ 启动 uvicorn。

## 必要配置

通过环境变量 / `.env` 配置（均有默认值，开箱即用）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PORT` | `8000` | 宿主机映射端口（容器内固定 8000）。如 `PORT=9000 docker compose up --build -d` |
| `DATABASE_PATH` | `/data/kiln.db` | SQLite 数据库文件路径，位于持久化卷 `kiln-data` |

## API 说明

基址：`http://localhost:8000`

### 1. 提交排程 `POST /plans`

请求体：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `kiln_capacity` | int | 单窑容量，正整数 |
| `pieces` | array | 1～14 件器物 |
| `pieces[].id` | int | 器物唯一编号，正整数 |
| `pieces[].volume` | int | 体积，正整数 |
| `pieces[].min_temp` | int | 允许温度区间下界（含），正整数 |
| `pieces[].max_temp` | int | 允许温度区间上界（含），需 `≥ min_temp` |

请求示例：

```bash
curl -s -X POST http://localhost:8000/plans \
  -H 'Content-Type: application/json' \
  -d '{
    "kiln_capacity": 10,
    "pieces": [
      {"id": 1, "volume": 6, "min_temp": 1000, "max_temp": 1200},
      {"id": 2, "volume": 5, "min_temp": 1100, "max_temp": 1250},
      {"id": 3, "volume": 4, "min_temp": 1280, "max_temp": 1320}
    ]
  }'
```

响应 `201 Created`（器物 1、2 体积之和 11 > 10 且与 3 温度无交集，故 1 单独一窑、2 单独一窑、3 单独一窑；窑序列按窑内最小编号升序）：

```json
{
  "id": "f1c2...-....",
  "kiln_count": 3,
  "kiln_capacity": 10,
  "kilns": [
    {"pieces": [1], "total_volume": 6, "firing_temp": 1000},
    {"pieces": [2], "total_volume": 5, "firing_temp": 1100},
    {"pieces": [3], "total_volume": 4, "firing_temp": 1280}
  ],
  "created_at": "2026-09-24T08:00:00.000000+00:00"
}
```

单件超容量返回 `400 Bad Request`：

```json
{ "detail": "器物 7 体积 20 超过单窑容量 10，无法装窑" }
```

器物编号重复、温度区间非法同样返回 400；字段缺失 / 超出 1～14 件 / 数值非正整数等结构错误返回 422。

### 2. 按 ID 读取方案 `GET /plans/{plan_id}`

```bash
curl -s http://localhost:8000/plans/f1c2...-....
```

找到返回 `200`（结构同上）；不存在返回：

```json
{ "detail": "方案不存在: f1c2...-...." }
```

状态码 `404`。

### 3. 健康检查 `GET /health`

```json
{ "status": "ok" }
```

## 算法说明（n ≤ 14）

1. 器物按编号升序映射到 n 个二进制位（位 0 = 最小编号）。
2. 对每个子集 `mask` 预计算：总体积、温度交集 `[max 下界, min 上界]` 以及是否可装同一窑。
3. 动态规划 `dp[mask]`：枚举包含 `mask` 最低位（剩余器物中编号最小者）的可行子集作为第一窑，
   `dp[mask] = min(1 + dp[mask \ 子窑])`，得到最少窑次（复杂度上界 O(3ⁿ)，n=14 时约 240 万次转移，亚秒级）。
4. 字典序重构：从全集开始，每一步在「仍能取得最少窑次」的第一窑候选中，选择编号元组字典序最小者，
   剩余部分递归求解；最后按窑内最小编号升序输出。
5. 单件超容量在 DP 前即校验并报错。

## 本地开发（不使用 Docker）

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_PATH=./kiln.db uvicorn app.main:app --reload --port 8000

# 运行算法单元测试（无需第三方依赖）
python -m unittest discover -s tests -v
```
