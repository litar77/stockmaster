# StockMaster Skill 安装指南

本文档提供 StockMaster A 股智能操盘 Skill 的详细安装步骤和配置说明。

---

## 📋 目录

1. [系统要求](#系统要求)
2. [快速安装](#快速安装)
3. [详细安装步骤](#详细安装步骤)
4. [OpenClaw 集成配置](#openclaw-集成配置)
5. [验证安装](#验证安装)
6. [常见问题](#常见问题)
7. [卸载](#卸载)

---

## 系统要求

### 基础要求

- **操作系统**：Windows 10/11, Linux, macOS
- **Python 版本**：Python 3.9 或更高版本
- **磁盘空间**：至少 500MB 可用空间
- **网络连接**：需要访问 AKShare 数据源

### 推荐配置

- **Python 环境**：使用虚拟环境（venv 或 conda）
- **内存**：4GB 以上
- **网络**：稳定的互联网连接（用于获取实时行情数据）

---

## 快速安装

### 一键安装脚本（推荐）

**Windows PowerShell：**
```powershell
# 克隆项目（如果是 Git 仓库）
# git clone <repository-url> stockmaster

# 进入项目目录
cd stockmaster\stockmaster

# 运行安装脚本
.\install.ps1
```

**Linux/macOS Bash：**
```bash
# 克隆项目
# git clone <repository-url> stockmaster

# 进入项目目录
cd stockmaster/stockmaster

# 运行安装脚本
chmod +x install.sh
./install.sh
```

### 手动快速安装

```bash
# 1. 进入项目目录
cd stockmaster/stockmaster

# 2. 创建虚拟环境（可选但推荐）
python -m venv .venv

# 3. 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 验证安装
python scripts/hq_analysis.py
```

---

## 详细安装步骤

### 步骤 1：检查 Python 环境

```bash
# 检查 Python 版本
python --version

# 应该显示 Python 3.9.x 或更高版本
```

**如果 Python 版本过低**，请前往 [Python 官网](https://www.python.org/downloads/) 下载最新版本。

### 步骤 2：创建项目目录

```bash
# 选择合适的项目位置
# Windows 示例：
cd C:\Users\YourName\Documents\projects

# Linux/macOS示例：
cd ~/projects

# 如果还未克隆项目，创建目录
mkdir stockmaster
cd stockmaster
```

### 步骤 3：创建虚拟环境（强烈推荐）

**为什么使用虚拟环境？**
- 避免依赖包冲突
- 便于管理和卸载
- 隔离项目环境

**创建虚拟环境：**
```bash
# 方法 1：使用 venv（Python 自带）
python -m venv .venv

# 方法 2：使用 conda（如果已安装）
conda create -n stockmaster python=3.9
conda activate stockmaster
```

**激活虚拟环境：**

| 操作系统 | 命令 |
|----------|------|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (CMD) | `.venv\Scripts\activate.bat` |
| Linux/macOS | `source .venv/bin/activate` |

激活成功后，命令行前缀应显示 `(.venv)`。

### 步骤 4：安装依赖包

**方式 1：使用 requirements.txt（推荐）**

```bash
pip install -r requirements.txt
```

**方式 2：手动安装核心依赖**

```bash
# 核心依赖（必需）
pip install akshare pandas numpy ta

# 可选依赖（可视化功能）
pip install matplotlib mplfinance

# 升级 akshare 到最新版本
pip install akshare --upgrade
```

**方式 3：使用国内镜像加速（中国大陆推荐）**

```bash
# 使用清华镜像源
pip install akshare pandas numpy ta -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 使用阿里云镜像
pip install akshare pandas numpy ta -i https://mirrors.aliyun.com/pypi/simple/
```

### 步骤 5：验证依赖安装

```bash
# 检查所有依赖是否正确安装
python -c "import akshare; import pandas; import numpy; import ta; print('✅ 所有依赖安装成功！')"
```

### 步骤 6：初始化项目配置

**创建持仓数据文件：**

```bash
# 进入项目目录
cd stockmaster/stockmaster

# 检查 data 目录是否存在
ls data  # Linux/macOS
dir data  # Windows

# 如果 portfolio.json 不存在，系统会在首次运行时自动创建
# 也可以手动创建示例文件
```

**示例 portfolio.json：**
```json
{
  "account": {
    "total_capital": 500000,
    "cash": 500000,
    "last_updated": "2026-03-27"
  },
  "holdings": [],
  "watchlist": [],
  "history": []
}
```

### 步骤 7：测试运行

```bash
# 测试行情分析模块
python scripts/hq_analysis.py

# 测试趋势分析
python scripts/trend_analyzer.py

# 测试持仓监控（需要先配置 portfolio.json）
python scripts/portfolio_monitor.py --strategy defensive
```

**预期输出：**
- JSON 格式的分析结果
- 生成的报告文件路径
- 无错误信息

---

## OpenClaw 集成配置

### 方式 1：作为 OpenClaw Skill 安装

**1. 复制 Skill 到 OpenClaw 目录**

```bash
# 假设 OpenClaw 安装在 /path/to/openclaw
cp -r stockmaster/stockmaster /path/to/openclaw/skills/stockmaster
```

**2. 配置 OpenClaw skills.yaml**

编辑 `/path/to/openclaw/config/skills.yaml`，添加：

```yaml
skills:
  - name: stockmaster
    enabled: true
    path: ./skills/stockmaster
    python_env: .venv/bin/python  # 或完整路径
    trigger_keywords:
      - 市场分析
      - 股票分析
      - 持仓查询
      - 买入信号
      - 卖出信号
```

**3. 配置定时任务**

编辑 `/path/to/openclaw/config/schedules.yaml`：

```yaml
schedules:
  - name: stockmaster_daily_report
    skill: stockmaster
    cron: "0 15:30 * * 1-5"  # 每周一至周五 15:30
    timezone: Asia/Shanghai
    workflow:
      - script: scripts/hq_analysis.py
        output: data/report.md
    notify:
      on_success: true
      on_failure: true
      channels:
        - wechat  # 或其他渠道
```

### 方式 2：作为独立脚本调用

**配置环境变量：**

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc（Linux/macOS）
# 或系统环境变量（Windows）

export STOCKMASTER_HOME="/path/to/stockmaster/stockmaster"
export PATH="$PATH:$STOCKMASTER_HOME/scripts"
```

**创建快捷命令：**

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
alias stockmaster-hq='python $STOCKMASTER_HOME/scripts/hq_analysis.py'
alias stockmaster-portfolio='python $STOCKMASTER_HOME/scripts/portfolio_monitor.py'
```

---

## 验证安装

### 基础验证

**1. 检查 Python 环境**

```bash
python --version
# 应显示 Python 3.9+

which python
# 应指向虚拟环境的 Python
```

**2. 检查依赖包**

```bash
pip list | grep -E "akshare|pandas|numpy|ta"
# 应显示所有核心依赖包
```

**3. 测试数据获取**

```bash
python -c "import akshare; df = ak.stock_zh_index_daily(symbol='sh000001'); print('✅ 数据获取成功！')"
```

### 功能验证

**运行完整测试：**

```bash
# 运行测试脚本
python scripts/test_chanlun.py

# 运行行情分析
python scripts/hq_analysis.py

# 检查生成的报告
ls -l data/HQ_*.md
ls -l data/CL_*.md
```

**预期结果：**
- ✅ 无错误信息
- ✅ 生成 HQ_yymmdd.md 文件
- ✅ 生成 CL_yymmdd.md 文件
- ✅ 报告内容完整

---

## 常见问题

### Q1: akshare 安装失败

**问题：**
```
ERROR: Could not find a version that satisfies the requirement akshare
```

**解决方案：**

```bash
# 方案 1：升级 pip
python -m pip install --upgrade pip
pip install akshare

# 方案 2：使用国内镜像
pip install akshare -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 方案 3：使用 conda 安装
conda install -c conda-forge akshare
```

### Q2: SSL 证书错误

**问题：**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**解决方案：**

```bash
# 方案 1：临时禁用 SSL 验证（不推荐）
pip install akshare --trusted-host pypi.org --trusted-host files.pythonhosted.org

# 方案 2：更新证书
pip install --upgrade certifi

# 方案 3：配置 pip
# 在 pip.conf 或 pip.ini 中添加：
[global]
trusted-host = pypi.org
               files.pythonhosted.org
```

### Q3: 数据获取超时

**问题：**
```
TimeoutError: Connection timed out
```

**解决方案：**

```bash
# 检查网络连接
ping akshare.xyz

# 检查防火墙设置
# Windows: 允许 Python 访问网络
# Linux: sudo ufw allow out 443

# 使用代理（如果需要）
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"
```

### Q4: 虚拟环境激活失败

**问题：**
```
Activate.ps1 cannot be loaded because running scripts is disabled on this system.
```

**解决方案（Windows PowerShell）：**

```powershell
# 修改执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或使用 CMD 激活
.venv\Scripts\activate.bat
```

### Q5: 报告文件未生成

**问题：**
运行脚本后找不到生成的报告文件

**解决方案：**

```bash
# 检查输出目录
ls data/

# 检查脚本输出
python scripts/hq_analysis.py 2>&1

# 检查文件权限
chmod 755 data/
```

---

## 卸载

### 方式 1：完整卸载

```bash
# 1. 停用虚拟环境（如果已激活）
deactivate

# 2. 删除虚拟环境目录
rm -rf .venv  # Linux/macOS
rmdir /s .venv  # Windows

# 3. 删除项目目录
cd ..
rm -rf stockmaster

# 4. 删除全局安装的依赖（如果使用全局 Python）
pip uninstall akshare pandas numpy ta
```

### 方式 2：保留配置卸载

```bash
# 仅删除虚拟环境和依赖，保留数据和配置
rm -rf .venv
rm -rf __pycache__

# 保留 data/ 和 config/ 目录
```

### 从 OpenClaw 卸载

```bash
# 1. 编辑 skills.yaml，移除 stockmaster 配置
# 2. 删除 Skill 目录
rm -rf /path/to/openclaw/skills/stockmaster

# 3. 重启 OpenClaw 服务
```

---

## 获取帮助

### 文档资源

- **项目文档**：`SKILL.md`
- **策略手册**：`references/` 目录
- **API 参考**：`references/akshare_api.md`

### 在线资源

- **AKShare 文档**：https://akshare.akfamily.xyz/
- **Pandas 文档**：https://pandas.pydata.org/docs/
- **TA-Lib 文档**：https://ta-lib.github.io/ta-lib-python/

### 技术支持

如遇到问题，请：
1. 查看本文档的"常见问题"部分
2. 检查项目 `SKILL.md` 文件
3. 查看相关策略文档

---

## 更新日志

### v1.0.0 (2026-03-27)
- ✅ 初始版本发布
- ✅ 集成缠论辅助判断
- ✅ 支持 OpenClaw 命令调用
- ✅ 完整的安装文档和脚本

---

**安装完成后，请继续查看 [SKILL.md](SKILL.md) 了解使用方法。**
