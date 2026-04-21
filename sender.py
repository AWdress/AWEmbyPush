#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import requests, os, time
import log
import wxapp
import tgbot
import bark
import traceback
from urllib.parse import quote as _url_quote

Sender = None


def build_play_url(media: dict) -> str:
    """构建媒体播放页面 URL，支持 Emby/Jellyfin 直链、Forward App 和 Infuse 协议"""
    watch_link_type = os.getenv("WATCH_LINK_TYPE", "server").lower()
    
    tmdb_id = media.get('media_tmdbid', '')
    imdb_id = media.get('media_imdbid', '')
    media_name = media.get('media_name', '')
    is_episode = media.get('media_type') == "Episode"
    tv_season = media.get('tv_season', 1)
    tv_episode = media.get('tv_episode', 1)

    if watch_link_type == "forward":
        # Forward App: forward://tmdb?id=xxx&type=movie/tv
        media_type = "tv" if is_episode else "movie"
        if tmdb_id:
            return f"forward://tmdb?id={tmdb_id}&type={media_type}"
        elif imdb_id:
            return f"forward://imdb?id={imdb_id}"
        else:
            return f"forward://search?q={media_name}"

    if watch_link_type == "infuse":
        # Infuse: infuse://movie/{tmdb_id} 或 infuse://series/{tmdb_id}-{season}-{episode}
        if tmdb_id:
            if is_episode:
                return f"infuse://series/{tmdb_id}-{tv_season}-{tv_episode}"
            else:
                return f"infuse://movie/{tmdb_id}"
        # Infuse 无 TMDB ID 时降级到服务器直链
    
    # 默认：Emby/Jellyfin 服务器直链
    server_url = media.get('server_url', '')
    server_id = media.get('server_id', '')
    media_id = media.get('media_id', '')
    server_type = media.get('server_type', 'Emby')
    
    if not server_url or not media_id:
        return server_url
    
    server_url = server_url.rstrip('/')
    
    if server_type.lower() == 'jellyfin':
        if server_id:
            return f"{server_url}/web/index.html#!/details?id={media_id}&serverId={server_id}"
        else:
            return f"{server_url}/web/index.html#!/details?id={media_id}"
    else:
        if server_id:
            return f"{server_url}/web/index.html#!/item?id={media_id}&serverId={server_id}"
        else:
            return f"{server_url}/web/index.html#!/item?id={media_id}"


def build_redirect_url(raw_url: str) -> str:
    """将 infuse:// / forward:// 等自定义协议 URL 包装成 HTTP 跳转链接。

    优先使用 LINK_REDIRECT_PREFIX 环境变量（支持 {url} 占位符），例如：
        https://jump.example.com/go.php?to={url}
    若未配置，则降级使用 REDIRECT_BASE_URL 指向内置 /open 端点，例如：
        http://192.168.1.100:8000  →  http://192.168.1.100:8000/open?url={encoded}
    两者均未配置则返回空字符串。
    """
    if not raw_url:
        return ""
    encoded = _url_quote(raw_url, safe="")

    prefix = os.getenv("LINK_REDIRECT_PREFIX", "").strip()
    if prefix and prefix.startswith(("http://", "https://")):
        if "{url}" in prefix:
            return prefix.replace("{url}", encoded)
        sep = "&" if "?" in prefix else "?"
        return f"{prefix}{sep}url={encoded}"

    base = os.getenv("REDIRECT_BASE_URL", "").rstrip("/")
    if base:
        return f"{base}/open?url={encoded}"

    return ""


class MessageSender:
    def send_welcome(self, welcome: dict):
        raise NotImplementedError

    def send_test_msg(self, test_content: str):
        raise NotImplementedError

    def send_media_details(self, media: dict):
        raise NotImplementedError


class TelegramSender(MessageSender):
    # 设置str属性，用于标识发送者
    def __str__(self):
        return "Telegram"
    
    def send_welcome(self, welcome: dict):
        msg = f"""🎬 {welcome['content']}

━━━━━━━━━━━━━━━━━━━━━━
👤 作者：{welcome['作者']}
📦 版本：{welcome['版本']}
📅 更新时间：{welcome['更新时间']}

📝 项目描述
{welcome['项目描述']}

🔗 项目地址
{welcome['项目地址']}
━━━━━━━━━━━━━━━━━━━━━━"""
        for ch in ["_", "*", "`", "["]:
            msg = msg.replace(ch, f"\\{ch}")
        tgbot.send_message(msg)

    def send_test_msg(self, test_content: str):
        for ch in ["_", "*", "`", "["]:
            test_content = test_content.replace(ch, f"\\{ch}")
        tgbot.send_message(test_content)

    def send_media_details(self, media: dict):
        # 参考原版样式设计
        server_name = media["server_name"]
        
        # 处理剧集信息
        if media["media_type"] == "Episode":
            if media.get("tv_episode_merged"):
                episode_info = f"第{media['tv_season']}季：第{media['tv_episode_range']}集 | 新更上线"
            else:
                episode_info = f"第{media['tv_season']}季：第{media['tv_episode']}集 | 新更上线"
            status_text = "新剧速递"
        else:
            episode_info = ""
            status_text = "新片速递"
        
        # 构建文案
        type_text = media.get("media_genres", "剧集" if media["media_type"] == "Episode" else "电影")
        release_date = media["media_rel"] if media["media_rel"] else "Unknown"
        date_label = "📺 首播" if media["media_type"] == "Episode" else "🎬 上映"
        
        # 标题部分 - 服务器名称 | 状态
        caption = f"<b>{server_name} | {status_text}</b>\n\n"
        caption += f"─────────────────────\n\n"
        
        # 片名
        caption += f"<b>【{media['media_name']}】</b>\n"
        
        # 剧集信息
        if episode_info:
            caption += f"{episode_info}\n\n"
        else:
            caption += "\n"
        
        # 元数据 - 分行显示
        if media.get('media_cast'):
            caption += f"👥 主演：{media['media_cast']}\n"
        caption += f"📺 类型：{type_text}\n"
        caption += f"⭐ 评分：{media['media_rating']}\n"
        caption += f"{date_label}：{release_date}\n"
        caption += "\n"
        
        # 简介 - 使用 HTML blockquote 标签（限制 150 字）
        if media.get('media_intro'):
            intro = media['media_intro']
            short_intro = intro[:150] + '...' if len(intro) > 150 else intro
            caption += f"📝 内容简介：\n<blockquote>{short_intro}</blockquote>\n\n"
        
        caption += f"─────────────────────"
        
        # 底部按钮
        enable_watch_link = os.getenv("ENABLE_WATCH_LINK", "false").lower() == "true"
        buttons = []
        if enable_watch_link:
            play_url = build_play_url(media)
            if play_url:
                if play_url.startswith(("http://", "https://")):
                    safe_play_url = play_url
                else:
                    safe_play_url = build_redirect_url(play_url)
                if safe_play_url:
                    buttons.append({"text": "▶️ 立即观看", "url": safe_play_url})
                else:
                    # 没有配置 REDIRECT_BASE_URL，降级把原始协议链接以文字形式附在正文末尾
                    caption += f"\n\n▶️ 立即观看\uFF1A{play_url}"
        buttons.append({"text": "ℹ️ 了解更多", "url": media['media_tmdburl']})
        reply_markup = {"inline_keyboard": [buttons]}
        
        # 使用剧照（Episode）或背景图（Movie）
        if media["media_type"] == "Episode":
            photo = media.get("media_still") or media.get("media_backdrop") or media.get("media_poster")
        else:
            photo = media.get("media_backdrop") or media.get("media_poster")
        
        tgbot.send_photo(caption, photo, reply_markup=reply_markup)


class WechatAppSender(MessageSender):
    def __str__(self):
        return "WechatApp"

    def send_welcome(self, welcome: dict):
        wxapp.send_welcome_card(welcome)

    def send_test_msg(self, test_content: str):
        wxapp.send_text(test_content)

    def send_media_details(self, media: dict):
        msgtype = os.getenv("WECHAT_MSG_TYPE", "news_notice")
        enable_watch_link = os.getenv("ENABLE_WATCH_LINK", "false").lower() == "true"
        
        # 构建剧集信息
        if media.get("media_type") == "Episode":
            if media.get("tv_episode_merged"):
                episode_text = f"第{media.get('tv_season')}季：第{media.get('tv_episode_range')}集"
                status_text = "新剧速递"
            else:
                episode_text = f"第{media.get('tv_season')}季：第{media.get('tv_episode')}集"
                status_text = "新剧速递"
        else:
            episode_text = ""
            status_text = "新片速递"
        
        type_text = media.get("media_genres", "剧集" if media.get("media_type") == "Episode" else "电影")
        release_date = media.get('media_rel') if media.get('media_rel') else 'Unknown'
        date_label = "📺 首播" if media.get("media_type") == "Episode" else "🎬 上映"
        
        if msgtype == "news_notice":
            # 卡片样式
            card_details = {
                "card_type": "news_notice",
                "source": {
                    "icon_url": f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{media.get('server_type', 'Emby').lower()}.png",
                    "desc": f"{media.get('server_name')} | {status_text}",
                    "desc_color": 0,
                },
                "main_title": {
                    "title": f"【{media.get('media_name')}】",
                    "desc": episode_text if episode_text else "新更上线"
                },
                "card_image": {
                    # 使用宽屏图片（剧照或背景图），降级到海报
                    "url": (media.get('media_still') or media.get('media_backdrop') or media.get('media_poster') or "") if media.get('media_type') == 'Episode' else (media.get('media_backdrop') or media.get('media_poster') or ""),
                    "aspect_ratio": 2.25,
                },
                "vertical_content_list": [
                    {
                        "title": "👥 主演",
                        "desc": f"{media.get('media_cast', '未知')}",
                    },
                    {
                        "title": "📺 类型",
                        "desc": type_text,
                    },
                    {
                        "title": "⭐ 评分",
                        "desc": f"{media.get('media_rating')}",
                    },
                    {
                        "title": date_label,
                        "desc": release_date,
                    },
                    {
                        "title": "📝 内容简介",
                        "desc": f"{media.get('media_intro', '')[:120] + '...' if len(media.get('media_intro', '')) > 120 else media.get('media_intro', '')}",
                    }
                ],
            }
            
            # 根据开关决定是否添加"立即观看"按钮
            tmdb_url = media.get('media_tmdburl', '') or ''
            if enable_watch_link:
                play_url = build_play_url(media)
                safe_play_url = ""
                if play_url:
                    if play_url.startswith(("http://", "https://")):
                        safe_play_url = play_url
                    else:
                        safe_play_url = build_redirect_url(play_url)
                if safe_play_url:
                    card_details["jump_list"] = [
                        {"type": 1, "url": safe_play_url, "title": "▶️ 立即观看"},
                        {"type": 1, "url": tmdb_url, "title": "ℹ️ 了解更多"},
                    ]
                    card_details["card_action"] = {"type": 1, "url": safe_play_url}
                else:
                    # 未配置 REDIRECT_BASE_URL，降级到 TMDB 链接
                    card_details["jump_list"] = [{"type": 1, "url": tmdb_url, "title": "ℹ️ 了解更多"}]
                    card_details["card_action"] = {"type": 1, "url": tmdb_url}
            else:
                card_details["jump_list"] = [{"type": 1, "url": tmdb_url, "title": "ℹ️ 了解更多"}]
                card_details["card_action"] = {"type": 1, "url": tmdb_url}
            
            wxapp.send_news_notice(card_details)
        elif msgtype == "news":
            # news 类型
            title_text = f"{media.get('server_name')} | {status_text} | 【{media.get('media_name')}】"
            if episode_text:
                title_text += f" | {episode_text}"
            
            date_label = "📺 首播" if media.get("media_type") == "Episode" else "🎬 上映"
            
            # 简介限制 100 字
            intro = media.get('media_intro', '')
            short_intro = intro[:100] + '...' if len(intro) > 100 else intro
            
            article = {
                "title": title_text,
                "description": f"👥 主演：{media.get('media_cast', '未知')}\n📺 类型：{type_text}\n⭐ 评分：{media.get('media_rating')}\n{date_label}：{release_date}\n\n📝 内容简介：{short_intro}" + (f"\n\nℹ️ 了解更多：{media.get('media_tmdburl')}" if enable_watch_link else ""),
                "url": (lambda p: p if p.startswith(("http://", "https://")) else (build_redirect_url(p) or media.get('media_tmdburl', '')))(build_play_url(media)) if enable_watch_link else media.get('media_tmdburl', ''),
                "picurl": media.get('media_still') or media.get('media_backdrop') or media.get('media_poster') or "" if media.get('media_type') == 'Episode' else media.get('media_backdrop') or media.get('media_poster') or ""
            }
            wxapp.send_news(article)


class BarkSender(MessageSender):
    def __str__(self):
        return "Bark"

    def send_welcome(self, welcome: dict):
        payload = {
            "title": f"🎬 {welcome['content']}",
            "body": f"👤 作者：{welcome['作者']}\n📦 版本：{welcome['版本']}\n📅 更新时间：{welcome['更新时间']}\n\n{welcome['项目描述']}",
            "url": f"{welcome['项目地址']}"
        }
        bark.send_message(payload)

    def send_test_msg(self, test_content: str):
        # test_content: This is a test message from *Aliyun_Shared*!
        # 将*中间的字符串提取出来作为server_name
        parts = test_content.split("*")
        server_name = parts[3] if len(parts) > 3 else "Unknown"
        payload = {
            "title": "🎉 AWEmbyPush Test",
            "body": f"恭喜！这是来自 {server_name} 的测试消息！现在您可以尝试向 Emby Server 添加新的媒体内容了~"
        }
        bark.send_message(payload)

    def send_media_details(self, media: dict):
        # 构建剧集信息
        release_date = media.get('media_rel') if media.get('media_rel') else 'Unknown'
        type_text = media.get("media_genres", "剧集" if media.get("media_type") == "Episode" else "电影")
        date_label = "📺 首播" if media.get("media_type") == "Episode" else "🎬 上映"
        enable_watch_link = os.getenv("ENABLE_WATCH_LINK", "false").lower() == "true"
        
        # 简短简介（前80字）
        intro = media.get('media_intro', '')
        short_intro = intro[:80] + '...' if len(intro) > 80 else intro
        
        if media.get("media_type") == "Episode":
            if media.get("tv_episode_merged"):
                episode_info = f"第{media.get('tv_season')}季：第{media.get('tv_episode_range')}集"
            else:
                episode_info = f"第{media.get('tv_season')}季：第{media.get('tv_episode')}集"
            status_text = "新剧速递"
            body_text = f"{episode_info} | 新更上线"
            if media.get('media_cast'):
                body_text += f"\n👥 主演：{media['media_cast']}"
            body_text += f"\n📺 类型：{type_text}\n⭐ 评分：{media['media_rating']}\n{date_label}：{release_date}"
            if short_intro:
                body_text += f"\n\n📝 内容简介：{short_intro}"
        else:
            status_text = "新片速递"
            body_text = ""
            if media.get('media_cast'):
                body_text += f"👥 主演：{media['media_cast']}\n"
            body_text += f"📺 类型：{type_text}\n⭐ 评分：{media['media_rating']}\n{date_label}：{release_date}"
            if short_intro:
                body_text += f"\n\n📝 内容简介：{short_intro}"
        
        if enable_watch_link:
            play_url = build_play_url(media)
            if play_url:
                if play_url.startswith(("http://", "https://")):
                    url_target = play_url
                else:
                    # 尝试用 302 中转；未配置中转地址时直接传入原始协议（iOS Bark 支持自定义协议）
                    url_target = build_redirect_url(play_url) or play_url
            else:
                url_target = media.get('media_tmdburl', '')
        else:
            url_target = media.get('media_tmdburl', '')
        payload = {
            "title": f"{media.get('server_name')} | {status_text}\n【{media['media_name']}】",
            "body": body_text,
            "icon": f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{media.get('server_type', 'Emby').lower()}.png",
            "url": url_target,
        }
        bark.send_message(payload)


class SenderManager:
    def __init__(self):
        self.senders = []
        self._initialize_senders()

    def _initialize_senders(self):
        tg_bot_token = os.getenv("TG_BOT_TOKEN")
        tg_chat_id = os.getenv("TG_CHAT_ID")
        if tg_bot_token and tg_chat_id:
            self.senders.append(TelegramSender())

        wechat_corp_id = os.getenv("WECHAT_CORP_ID")
        wechat_corp_secret = os.getenv("WECHAT_CORP_SECRET")
        wechat_agent_id = os.getenv("WECHAT_AGENT_ID")
        if wechat_corp_id and wechat_corp_secret and wechat_agent_id:
            self.senders.append(WechatAppSender())

        bark_server = os.getenv("BARK_SERVER")
        bark_device_keys = os.getenv("BARK_DEVICE_KEYS")
        log.logger.debug(f"bark_server: {bark_server}, bark_device_keys: {bark_device_keys}")
        if bark_server and bark_device_keys:
            self.senders.append(BarkSender())

    def send_welcome(self, welcome_message: dict):
        for sender in self.senders:
            try:
                sender.send_welcome(welcome_message)
            except ValueError as e:
                print(f"Error {sender} sending welcome message: {e}")

    def send_test_msg(self, test_content):
        for sender in self.senders:
            try:
                sender.send_test_msg(test_content)
            except:
                log.logger.error(f"Error sending test message by {sender}")
                log.logger.error(traceback.format_exc())
                continue

    def send_media_details(self, media):
        for sender in self.senders:
            try:
                sender.send_media_details(media)
            except:
                log.logger.error(f"Error sending media details by {sender}")
                log.logger.error(traceback.format_exc())
                continue