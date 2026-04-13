# 更新日志 / Changelog

## [v4.5.6] - 2026-04-13

### 🎨 优化 / Improvements

- Telegram "立即观看"和"了解更多"从 HTML 链接改为 inline keyboard button（底部按钮样式）

## [v4.5.5] - 2026-04-12

### 🐛 Bug 修复 / Bug Fixes

- 修复电影和电视剧入库重复推送的 bug
- 改进消息指纹去重策略：电影用 ProviderIds（TMDB/IMDB ID），电视剧用 SeriesName + 季 + 集，不再依赖不稳定的 Webhook Title 字段
- 新增发送层去重机制（`_sent_records`），基于 TMDB ID 在真正推送前做最终拦截（5分钟窗口，可通过 `SEND_DEDUP_WINDOW` 环境变量配置）

## [v4.5.4] - 2026-03-20

### ✨ 新增功能 / New Features

- 所有渠道支持"立即观看"和"了解更多"按钮（Bark、微信 news/news_notice、Telegram）
- Bark 标题支持多行格式（与 Telegram 一致）

### 🐛 Bug 修复 / Bug Fixes

- 修复重复通知根本原因：在 HTTP 层（handle_post）增加请求体哈希去重，30秒内相同请求直接拦截，不再入队
- 修复微信卡片 `card_image.url` 在图片为 None 时显示 "None" 字符串
- 修复微信 news `picurl` 字段可能为 None 的问题
- 修复微信 news description 改为垂直格式显示
- 修复各渠道简介前缺少"📝 内容简介："标签
- 移除 Bark `actions` 字段（Bark API 不支持此字段）
- 修复 Bark `send_test_msg` 中 `split("*")[3]` 可能越界的问题
- 修复 Bark `send_media_details` 中 `enable_watch_link` 变量未定义就使用的问题

## [v4.5.3] - 2026-03-19

### 🐛 Bug 修复 / Bug Fixes

- 剧集评分改用电视剧总评分，而非单集评分

## [v4.5.2] - 2026-03-13

### ✨ 新增功能 / New Features

- "立即观看"按钮现在跳转到具体影片播放页面，而非服务器首页
- 自动识别 Emby/Jellyfin 服务器类型，使用对应的 URL 格式
- 支持电影和剧集的精准跳转

### 🎨 优化 / Improvements

- 限制简介长度，避免通知过长
  - Telegram: 150 字
  - 企业微信 news_notice: 120 字
  - 企业微信 news: 100 字
  - Bark: 80 字（保持不变）

### 🐛 Bug 修复 / Bug Fixes

- 修复 TMDB 搜索结果为空时的 IndexError 异常
- 修复 Jellyfin 消息缺少 Server.Id 和 Item.Id
- 修复 Emby 消息可能缺少 Server.Id 的问题
- 修复 parse_info 中直接访问字段可能导致的 KeyError
- 修复 build_play_url 在 server_id 为空时生成错误 URL

### 🔧 技术细节 / Technical Details

- 新增 `build_play_url()` 函数构建播放页面 URL
- 保存媒体 ID (`media_id`) 和服务器 ID (`server_id`)
- Emby URL 格式：`/web/index.html#!/item?id=xxx&serverId=xxx`
- Jellyfin URL 格式：`/web/index.html#!/details?id=xxx&serverId=xxx`
- 使用 `.get()` 方法安全访问字段，避免 KeyError

## [v4.5.1] - 2026-03-11

### 🐛 Bug 修复 / Bug Fixes

- 修复所有主演 emoji 显示为 👥
- 修复企业微信 news_notice 卡片元数据垂直显示
- 修复企业微信 news 消息元数据垂直显示

### 🎨 样式优化 / Style Improvements

- Telegram 改用 HTML 格式
- 简介使用 `<blockquote>` 标签实现引用效果（粉色背景 + 左侧竖线）
- 优化 Telegram 链接和粗体显示

## [v4.5.0] - 2026-03-11

### 🎨 新增功能 / New Features

#### 主演信息显示
- 新增主演信息显示，展示前 5 位主演
- 从 TMDB API 自动获取演员信息
- 支持 Telegram、WeChat、Bark 三个推送渠道

#### TMDB 类型显示
- 使用 TMDB 的 Genres 显示更详细的类型信息（如"动作, 冒险, 剧情"）
- 自动翻译英文类型为中文，包含完整的类型映射表
- 无类型信息时降级显示"电影"或"剧集"

#### 简介优化
- Telegram 简介使用引用格式（blockquote），提升视觉层次
- 单集无简介时自动使用电视剧总简介作为备用
- Bark 显示简短简介（前 80 字），避免通知过长

#### 日期标签优化
- 电影显示"🎬 上映"，剧集显示"📺 首播"
- 更加专业和准确的日期标签

### 🔧 优化 / Improvements

- 优化元数据显示顺序：主演 → 类型 → 评分 → 日期
- 优化 API 调用，避免重复请求 TMDB
- 完善错误处理和降级策略

### 📝 技术细节 / Technical Details

- 新增 `tmdb_api.get_movie_credits()` 和 `tmdb_api.get_tv_credits()` 函数
- 新增 `tmdb_api.translate_genre()` 类型翻译函数
- 新增 `media_cast` 和 `media_genres` 字段
- 优化 Episode 类避免重复调用 `get_tv_details`

## [v4.4.1] - 2026-03-11

### 🎨 样式优化 / Style Improvements

- 优化通知样式，统一三个推送渠道（Telegram、WeChat、Bark）的显示格式
- 标题格式改为：`服务器名 | 新剧速递/新片速递`
- 片名使用中文括号格式：`【片名】`
- 剧集信息格式：`第X季：第X集 | 新更上线`
- 元数据垂直显示：⭐ 评分、📺 类型（剧集/电影）、📅 日期（完整日期）
- 添加 📝 内容简介部分（Telegram 和 WeChat）
- 使用细横线分隔符（`─`）提升视觉效果
- 类型字段简化为"剧集"或"电影"，不再显示 Genres

## [v4.4.0] - 2026-03-11

### 🎨 新增功能 / New Features

#### Netflix 风格通知
- 全新的 Netflix 风格通知样式设计
- 采用宽屏剧照/背景图展示，视觉冲击力更强
- 优化信息层次，状态提示更清晰（"新剧集已上线"/"新电影已上线"）
- 元数据横向排列（评分 | 类型 | 年份），一目了然
- 支持 Telegram、企业微信、Bark 三种推送渠道

#### 立即观看按钮
- 新增 `ENABLE_WATCH_LINK` 环境变量控制（默认关闭）
- 支持直接跳转到媒体服务器
- Jellyfin 自动获取服务器地址
- Emby 用户可通过 `EMBY_SERVER_URL` 配置服务器地址
- 默认关闭以保护服务器地址隐私

### 🐛 Bug 修复 / Bug Fixes

- 修复 `media_rel` 为 None 时的崩溃问题
- 修复企业微信 news_notice 卡片年份显示错误
- 修复企业微信 news 消息年份显示错误
- 修复 Bark 推送电影年份显示错误
- 完善边界情况处理，避免空值错误
- 优化图片选择逻辑，支持降级策略

### 📝 文档更新 / Documentation

- 新增 `NETFLIX_STYLE_CONFIG.md` - Netflix 风格详细配置文档
- 新增 `BUG_CHECK_REPORT.md` - Bug 检查报告
- 新增 `FIXES_SUMMARY.md` - 修复总结
- 新增 `test_netflix_style.py` - 测试脚本
- 更新 README.md，添加新环境变量说明
- 完善环境变量配置文档

### 🔧 技术改进 / Technical Improvements

- 所有字符串切片操作添加 None 值检查
- 环境变量解析更加健壮，支持大小写不敏感
- 代码质量提升，通过完整的单元测试
- 添加 28 个测试用例，覆盖所有关键功能

### 📦 新增环境变量 / New Environment Variables

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ENABLE_WATCH_LINK` | 是否显示"立即观看"按钮 | `false` |
| `EMBY_SERVER_URL` | Emby 服务器地址 | `https://emby.media` |

---

## [v4.3.5] - 2025-11-22

### 🆕 新增功能

#### 消息去重机制
- 60秒内相同消息只处理一次，自动拦截 Emby/Jellyfin 重复推送
- 同一集在缓存中只保留一份，避免重复计数
- 单集不再显示"共1集"，改为正常单集展示
- 电影重复推送自动拦截，避免骚扰通知
- 新增 `MESSAGE_DEDUP_WINDOW` 环境变量，可自定义去重时间窗口

### 🐛 Bug 修复

- 修复剧集合并显示问题
- 优化缓存管理逻辑

---

## [v4.3.0] - 2025-10-15

### 🆕 新增功能

#### 电视剧集合并推送
- 自动合并同一电视剧的多集推送
- 支持连续集数范围显示（如：第1-10集）
- 支持不连续集数列表显示（如：第1,3,5集）
- 新增 `EPISODE_CACHE_TIMEOUT` 环境变量，可自定义缓存时间

### 🔧 技术改进

- 优化推送逻辑，减少通知频率
- 改进缓存管理机制

---

## [v4.2.0] - 2025-09-01

### 🆕 新增功能

#### 企业微信代理支持
- 新增 `WECHAT_PROXY_URL` 环境变量
- 支持 2022年6月20日后创建的自建应用
- 完善企业微信推送功能

### 🐛 Bug 修复

- 修复企业微信推送失败问题
- 优化错误处理逻辑

---

## [v4.1.0] - 2025-07-15

### 🆕 新增功能

#### Bark 推送支持
- 新增 Bark iOS 通知推送
- 支持多设备推送
- 支持自定义 Bark 服务器

### 🔧 技术改进

- 优化推送渠道管理
- 改进错误日志输出

---

## [v4.0.0] - 2025-05-01

### 🆕 新增功能

#### 多推送渠道支持
- 支持 Telegram Bot 推送
- 支持企业微信推送
- 支持同时配置多个推送渠道

#### TMDB/TVDB 集成
- 自动获取媒体详细信息
- 支持海报、剧照、背景图
- 支持评分、简介等元数据

### 🔧 技术改进

- 重构代码架构
- 优化性能和稳定性
- 完善错误处理

---

## 版本说明 / Version Notes

### 版本号规则
- 主版本号：重大架构变更或不兼容更新
- 次版本号：新功能添加
- 修订号：Bug 修复和小改进

### 升级建议
- v4.3.x → v4.4.0: 平滑升级，向后兼容
- 新增环境变量为可选配置，不影响现有功能
- 建议查看 `NETFLIX_STYLE_CONFIG.md` 了解新功能

### 反馈与支持
- GitHub Issues: https://github.com/AWdress/AWEmbyPush/issues
- 项目主页: https://github.com/AWdress/AWEmbyPush
