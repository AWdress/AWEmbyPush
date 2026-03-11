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
        # Netflix 风格设计
        server_name = media["server_name"]
        for ch in ["_", "*", "`", "["]:
            server_name = server_name.replace(ch, f"\\{ch}")
        
        # 处理剧集信息
        if media["media_type"] == "Episode":
            if media.get("tv_episode_merged"):
                # 合并剧集
                episode_info = f"第{media['tv_season']}季：第{media['tv_episode_range']}集"
                status_text = "新剧集已上线"
            else:
                # 单集
                episode_info = f"第{media['tv_season']}季：第{media['tv_episode']}集"
                status_text = "新剧集已上线"
        else:
            # 电影
            episode_info = ""
            status_text = "新电影已上线"
        
        # 构建 Netflix 风格的文案
        type_emoji = "📺" if media["media_type"] == "Episode" else "🎬"
        type_text = "剧集" if media["media_type"] == "Episode" else "电影"
        year = media["media_rel"][0:4] if media["media_rel"] else "Unknown"
        
        # 标题部分
        caption = f"🎬 {server_name}\n\n"
        caption += f"{status_text}\n\n"
        caption += f"*{media['media_name']}*\n"
        caption += f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # 剧集信息（如果是剧集）
        if episode_info:
            caption += f"{episode_info}\n\n"
        
        # 元数据行
        caption += f"⭐ {media['media_rating']} | {type_emoji} {type_text} | 🗓️ {year}\n\n"
        
        # 简介
        caption += f"{media['media_intro']}\n\n"
        
        # 底部链接 - 根据开关决定是否显示"立即观看"
        enable_watch_link = os.getenv("ENABLE_WATCH_LINK", "false").lower() == "true"
        if enable_watch_link:
            caption += f"▶️ [立即观看]({media['server_url']}) | ℹ️ [了解更多]({media['media_tmdburl']})\n"
        else:
            caption += f"ℹ️ [了解更多]({media['media_tmdburl']})\n"
        
        # 使用剧照（Episode）或背景图（Movie）作为宽屏展示
        if media["media_type"] == "Episode":
            # 优先使用剧照，如果没有则使用海报
            photo = media.get("media_still") or media.get("media_backdrop") or media.get("media_poster")
        else:
            # 电影使用背景图
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
        
        # Netflix 风格：构建剧集信息
        if media.get("media_type") == "Episode":
            if media.get("tv_episode_merged"):
                episode_text = f"第{media.get('tv_season')}季：第{media.get('tv_episode_range')}集"
                status_text = "新剧集已上线"
            else:
                episode_text = f"第{media.get('tv_season')}季：第{media.get('tv_episode')}集"
                status_text = "新剧集已上线"
        else:
            episode_text = ""
            status_text = "新电影已上线"
        
        if msgtype == "news_notice":
            # Netflix 风格卡片
            card_details = {
                "card_type": "news_notice",
                "source": {
                    "icon_url": f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{media.get('server_type', 'Emby').lower()}.png",
                    "desc": f"🎬 {media.get('server_name')}",
                    "desc_color": 0,
                },
                "main_title": {
                    "title": f"{status_text}",
                    "desc": f"{media.get('media_name')}"
                },
                "card_image": {
                    # 使用宽屏图片（剧照或背景图）
                    "url": f"{media.get('media_still') if media.get('media_type') == 'Episode' else media.get('media_backdrop')}",
                    "aspect_ratio": 2.25,
                },
                "vertical_content_list": [
                    {
                        "title": episode_text if episode_text else f"{media.get('media_name')}",
                        "desc": f"{media.get('media_intro')}",
                    }
                ],
                "horizontal_content_list": [
                    {"keyname": "⭐ 评分", "value": f"{media.get('media_rating')}"},
                    {"keyname": "📺 类型", "value": f"{'剧集' if media.get('media_type') == 'Episode' else '电影'}"},
                    {"keyname": "🗓️ 年份", "value": f"{media.get('media_rel')[:4] if media.get('media_rel') else 'Unknown'}"},
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
            # Netflix 风格 news 类型
            title_text = f"🎬 {status_text} | {media.get('media_name')}"
            if episode_text:
                title_text += f" | {episode_text}"
            
            article = {
                "title": title_text,
                "description": f"⭐ {media.get('media_rating')} | 🗓️ {media.get('media_rel')[:4] if media.get('media_rel') else 'Unknown'} | {media.get('media_intro')}",
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
        # Netflix 风格：构建剧集信息
        year = media.get('media_rel')[:4] if media.get('media_rel') else 'Unknown'
        
        if media.get("media_type") == "Episode":
            if media.get("tv_episode_merged"):
                episode_info = f"第{media.get('tv_season')}季：第{media.get('tv_episode_range')}集"
                status_text = "新剧集"
            else:
                episode_info = f"第{media.get('tv_season')}季：第{media.get('tv_episode')}集"
                status_text = "新剧集"
            body_text = f"{episode_info}已上线 | ⭐ {media['media_rating']} | {media.get('server_name')}"
        else:
            status_text = "新电影"
            body_text = f"⭐ {media['media_rating']} | 🗓️ {year} | {media.get('server_name')}"
        
        payload = {
            "title": f"🎬 {status_text} | {media['media_name']}",
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