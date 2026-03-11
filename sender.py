#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import requests, os, time
import log
import wxapp
import tgbot
import bark
import traceback

Sender = None


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
        for ch in ["_", "*", "`", "["]:
            server_name = server_name.replace(ch, f"\\{ch}")
        
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
        caption = f"*{server_name} | {status_text}*\n\n"
        caption += f"─────────────────────\n\n"
        
        # 片名
        caption += f"*【{media['media_name']}】*\n"
        
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
        
        # 简介 - 使用 Markdown 引用格式
        if media.get('media_intro'):
            # 将简介的每一行前面加上 > 符号
            intro_lines = media['media_intro'].split('\n')
            quoted_intro = '\n'.join([f">{line}" if line.strip() else ">" for line in intro_lines])
            caption += f"📝 内容简介：\n{quoted_intro}\n\n"
        
        caption += f"─────────────────────\n\n"
        
        # 底部链接
        enable_watch_link = os.getenv("ENABLE_WATCH_LINK", "false").lower() == "true"
        if enable_watch_link:
            caption += f"▶️ [立即观看]({media['server_url']}) | ℹ️ [了解更多]({media['media_tmdburl']})\n"
        else:
            caption += f"ℹ️ [了解更多]({media['media_tmdburl']})\n"
        
        # 使用剧照（Episode）或背景图（Movie）
        if media["media_type"] == "Episode":
            photo = media.get("media_still") or media.get("media_backdrop") or media.get("media_poster")
        else:
            photo = media.get("media_backdrop") or media.get("media_poster")
        
        tgbot.send_photo(caption, photo)


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
                    # 使用宽屏图片（剧照或背景图）
                    "url": f"{media.get('media_still') if media.get('media_type') == 'Episode' else media.get('media_backdrop')}",
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
                        "desc": f"{media.get('media_intro')}",
                    }
                ],
            }
            
            # 根据开关决定是否添加"立即观看"按钮
            if enable_watch_link:
                card_details["jump_list"] = [
                    {
                        "type": 1,
                        "url": f"{media.get('server_url')}",
                        "title": "▶️ 立即观看",
                    },
                    {
                        "type": 1,
                        "url": f"{media.get('media_tmdburl')}",
                        "title": "ℹ️ 了解更多",
                    },
                ]
                card_details["card_action"] = {"type": 1, "url": f"{media.get('server_url')}"}
            else:
                card_details["jump_list"] = [
                    {
                        "type": 1,
                        "url": f"{media.get('media_tmdburl')}",
                        "title": "ℹ️ 了解更多",
                    },
                ]
                card_details["card_action"] = {"type": 1, "url": f"{media.get('media_tmdburl')}"}
            
            wxapp.send_news_notice(card_details)
        elif msgtype == "news":
            # news 类型
            title_text = f"{media.get('server_name')} | {status_text} | 【{media.get('media_name')}】"
            if episode_text:
                title_text += f" | {episode_text}"
            
            date_label = "📺 首播" if media.get("media_type") == "Episode" else "🎬 上映"
            
            article = {
                "title": title_text,
                "description": f"👥 主演：{media.get('media_cast', '未知')}\n📺 类型：{type_text}\n⭐ 评分：{media.get('media_rating')}\n{date_label}：{release_date}\n\n📝 内容简介：{media.get('media_intro')}",
                "url": f"{media.get('media_tmdburl')}",
                "picurl": f"{media.get('media_still') if media.get('media_type') == 'Episode' else media.get('media_backdrop')}"
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
        server_name = test_content.split("*")[3]
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
                body_text += f"\n\n📝 {short_intro}"
        else:
            status_text = "新片速递"
            body_text = ""
            if media.get('media_cast'):
                body_text += f"👥 主演：{media['media_cast']}\n"
            body_text += f"📺 类型：{type_text}\n⭐ 评分：{media['media_rating']}\n{date_label}：{release_date}"
            if short_intro:
                body_text += f"\n\n📝 {short_intro}"
        
        payload = {
            "title": f"{media.get('server_name')} | {status_text}\n【{media['media_name']}】",
            "body": body_text,
            "icon": f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{media.get('server_type', 'Emby').lower()}.png",
            "url": f"{media['media_tmdburl']}",
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