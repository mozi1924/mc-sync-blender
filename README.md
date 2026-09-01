# Yefira (MC Sync Blender)

[![Fabric](https://img.shields.io/badge/Fabric-Mod-blue.svg)](https://fabricmc.net/)
[![License](https://img.shields.io/badge/License-GPL_3.0-blue.svg)](LICENSE)
[![Blender](https://img.shields.io/badge/Companion-MoziToolKit-orange.svg)](https://github.com/mozi1924/MoziToolKit)

**Yefira** 是专为 **Minecraft (Fabric)** 与 **Blender ([MoziToolKit](https://github.com/mozi1924/MoziToolKit))** 打造的高性能、低延迟实时双向同步模组。

通过内置轻量化 WebSocket 通信架构与高频方块状态编码器，Yefira 能够将游戏内指定 3D 选区的方块数据、增量变化实时推送至 Blender 视口中构建三维点云与模型；同时支持类似 Blender 视口的 Ghost 模式自由漫游与射线选区操作。

---

## ✨ 核心特性 (Features)

1. **⚡ 毫秒级方块差异增量同步 (Real-time Delta Sync)**
   - 监听服务端与客户端的世界方块变更 (`setBlock`)，通过变长整数 (`VarInt`) 与压缩调色板进行超轻量编码，单 Tick 内聚合推送差异，零延迟联动 Blender 视口。
2. **🎯 3D 视觉选区系统 (3D Visual Selection)**
   - 支持高亮线框与半透明体积填充渲染；
   - 快捷金镐交互（左键设 Pos1，右键设 Pos2）；
   - 游戏内完整指令 `/yefira` 支持。
3. **👻 Blender 风格幽灵摄像机 (Ghost Mode & Fly Navigation)**
   - **自由观察**：解耦玩家身体与摄像机，在世界中自由穿透、平移（中键拖拽/WASD平移）；
   - **飞行漫游 (Fly Navigation)**：类似 Blender `Shift + ~` 的平滑视角漫游体验；
   - **射线投射拖选**：无需物理移动即可在视口中点击方块拖拽出立体选区。
4. **🌐 双端运行模式 (Client / Server Dual Mode)**
   - **单人游戏 / 本地客户端**：一键直连本地 Blender 插件；
   - **多人服务器**：支持专用服务器运行，多玩家协同编辑并向 Blender 工作站广播。
5. **💾 选区持久化与自动恢复**
   - 选区数据自动按世界目录隔离存储 (`.yefira_selection.dat`)，重进世界无缝恢复。

---

## 📦 兼容性与运行环境 (Compatibility & Requirements)

### 1. 运行依赖 (Dependencies)
| 依赖项 | 最低要求 / 推荐版本 | 说明 |
| :--- | :--- | :--- |
| **Fabric Loader** | `>= 0.14.0` (推荐最新) | 模组加载器 |
| **Fabric API** | 对应 MC 版本最新版 | 提供事件与生命周期钩子 |
| **Java Runtime** | Java 21+ (MC 1.20.5+) / Java 17 (MC 1.18 - 1.20.4) | 依据 Minecraft 版本 |
| **Java-WebSocket** | `1.5.6` | **已内置 (Shadowed/Included)**，无需额外安装 |
| **Blender 插件** | [MoziToolKit](https://github.com/mozi1924/MoziToolKit) (4.2+ LTS) | Blender 端实时接收与渲染器 |

### 2. Minecraft 版本适配规划 (Version Support Matrix)
| 版本梯队 | Minecraft 版本 | 适配状态 | 说明 |
| :--- | :--- | :--- | :--- |
| **主线开发 (Mainline)** | `26.2` / `1.21.4+` | 🟢 官方支持 | 最新版 API 与 Gizmo 视口渲染体系 |
| **主流 LTS 现代化版本** | `1.20.1` / `1.21.1` | 🟡 计划向下兼容 | 社区主流模组包推荐版本 |
| **长期经典版本** | `1.16.5` / `1.19.2` | 🔵 规划中 | 适配经典历史模组生态 |

> [!NOTE]
> Yefira 的网络通信协议（JSON RPC + WebSocket 二进制/文本载荷）是**版本无关 (Version-Agnostic)** 的。跨版本适配主要涉及 Minecraft 内部渲染器（`Gizmos` / `WorldRenderEvents`）与输入事件系统的接口平移。

---

## 🎮 控制与快捷键 (Controls & Shortcuts)

| 快捷键 (默认) | 功能说明 | 适用场景 |
| :--- | :--- | :--- |
| <kbd>F6</kbd> | 开启 / 关闭 **幽灵摄像机模式 (Ghost Mode)** | 全局 |
| <kbd>F7</kbd> | 打开 **Yefira 设置与控制面板 GUI** | 全局 |
| <kbd>~</kbd> / <kbd>Shift + ~</kbd> | 开启 / 退出 **飞行漫游视角 (Fly Navigation)** | 幽灵模式下 |
| <kbd>Numpad .</kbd> | 视口居中聚焦至当前选区 (Focus Selection) | 幽灵模式下 |
| <kbd>Delete</kbd> | 清空当前已选区域 | 幽灵模式下 |
| <kbd>B</kbd> | 在光标/准星处创建 16×16×16 预设区域 | 幽灵模式下 |
| <kbd>ESC</kbd> | 退出飞行漫游 / 取消当前正在拖拽的选区 | 幽灵模式下 |

---

## ⌨️ 游戏内指令 (Commands)

```text
/yefira pos1 [<x> <y> <z>]   # 设置选区起点（不填坐标则为当前脚下）
/yefira pos2 [<x> <y> <z>]   # 设置选区终点
/yefira set <x1> <y1> <z1> <x2> <y2> <z2> # 一键指定立体选区
/yefira clear                # 清空当前选区
/yefira info                 # 查看当前选区坐标、尺寸与体积
/yefira export               # 手动触发一次全量选区方块数据导出至 Blender
/yefira server <start|stop|status|restart> # 控制内部 WebSocket 服务
/yefira reload               # 重新加载配置文件 (config/yefira.json)
```

---

## ⚙️ 配置文件 (Configuration)

模组配置文件位于 `.minecraft/config/yefira.json`：

```json
{
  "host": "127.0.0.1",
  "port": 24892,
  "autoStartOnWorldLoad": true,
  "legacyPickaxeMode": true
}
```

* `host`: WebSocket 监听绑定的 IP 地址（默认 `127.0.0.1` 本地回环，若多机联机可配 `0.0.0.0`）。
* `port`: WebSocket 端口（默认 `24892`，需与 Blender MoziToolKit 设置一致）。
* `autoStartOnWorldLoad`: 进入单人世界或服务器启动时是否自动启动 WebSocket 服务。
* `legacyPickaxeMode`: 是否启用手持金镐快捷点击方块设置选区。

---

## 🛠️ 构建与开发 (Building & Development)

### 编译 Mod Jar
```bash
./gradlew build
```
编译产物位于 `build/libs/yefira-<version>.jar`。

### 运行测试用例
```bash
./gradlew test
```

### 启动测试客户端
```bash
./gradlew runClient
```

---

## 📄 开源许可 (License)

本项目采用 [GNU General Public License v3.0 (GPL-3.0)](LICENSE) 许可开源。
