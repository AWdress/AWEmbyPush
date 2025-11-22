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
        caption = (
            "#影视更新 #{server_name}\n"
            + "\[{type_ch}]\n"
            + "片名： *{title}* ({year})\n"
            + "{episode}"
            + "评分： {rating}\n\n"
            + "上映日期： {rel}\n\n"
            + "内容简介： {intro}\n\n"
            + "相关链接： [TMDB]({tmdb_url})\n"
        )
        server_name = media["server_name"]
        for ch in ["_", "*", "`", "["]:
            server_name = server_name.replace(ch, f"\\{ch}")
        
        # 处理合并剧集的显示
        if media.get("tv_episode_merged"):
            # 区分连续和不连续集数的显示
            if media.get("tv_episode_continuous"):
                episode_text = f"已更新至 第{media['tv_season']}季 第{media['tv_episode_range']}集 (共{media['tv_episode_count']}集)\n"
            else:
                episode_text = f"已更新 第{media['tv_season']}季 第{media['tv_episode_range']}集 (共{media['tv_episode_count']}集)\n"
            title = media["media_name"]
        else:
            episode_text = f"已更新至 第{media['tv_season']}季 第{media['tv_episode']}集\n" if media["media_type"] == "Episode" else ""
            title = media["media_name"]
        
        caption = caption.format(
            server_name=server_name,
            type_ch="电影" if media["media_type"] == "Movie" else "剧集",
            title=title,
            # 部分电视剧没有 air_date 导致无法获取当前剧集的上映年份，增加年份字段判断保护
            year=media["media_rel"][0:4] if media["media_rel"] else "Unknown",
            episode=episode_text,
            rating=media["media_rating"],
            rel=media["media_rel"],
            intro=media["media_intro"],
            tmdb_url=media["media_tmdburl"],
        )
        poster = media["media_poster"]
        tgbot.send_photo(caption, poster)


class WechatAppSender(MessageSender):
    def __str__(self):
        return "WechatApp"

    def send_welcome(self, welcome: dict):
        wxapp.send_welcome_card(welcome)

    def send_test_msg(self, test_content: str):
        wxapp.send_text(test_content)

    def send_media_details(self, media: dict):
        msgtype = os.getenv("WECHAT_MSG_TYPE", "news_notice")
        if msgtype == "news_notice":
            card_details = {
                "card_type": "news_notice",
                "source": {
                    "icon_url": f"https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/{media.get('server_type', 'Emby').lower()}.png",
                    "desc": f"{media.get('server_type')} Server",
                    "desc_color": 0,
                },
                "main_title": {
                    "title": f"#{media.get('server_name')} 影视更新",
                },
                "card_image": {
                    "url": f"{media.get('media_backdrop') if media.get('media_type') == 'Movie' else media.get('media_still')}",
                    "aspect_ratio": 2.25,
                },
                "vertical_content_list": [
                    {
                        "title": f"[{'电影' if media.get('media_type') == 'Movie' else '剧集'}] {media.get('media_name')} ({media.get('media_rel')[:4]})"
                        + (
                            f" 第 {media.get('tv_season')} 季 | 第 {media.get('tv_episode_range')} 集 (共{media.get('tv_episode_count')}集)"
                            if media.get("tv_episode_merged")
                            else (
                                f" 第 {media.get('tv_season')} 季 | 第 {media.get('tv_episode')} 集"
                                if media.get("media_type") == "Episode"
                                else ""
                            )
                        ),
                        "desc": f"{media.get('media_intro')}",
                    }
                ],
                "horizontal_content_list": [
                    {"keyname": "上映日期", "value": f"{media.get('media_rel')}"},
                    {"keyname": "评分", "value": f"{media.get('media_rating')}"},
                ],
                "jump_list": [
                    {
                        "type": 1,
                        "url": f"{media.get('media_tmdburl')}",
                        "title": "TMDB",
                    },
                ],
                "card_action": {"type": 1, "url": f"{media.get('server_url')}"},
            }
            wxapp.send_news_notice(card_details)
        elif msgtype == "news":
            article = {
                "title" : f"[影视更新][{'电影' if media.get('media_type') == 'Movie' else '剧集'}] {media.get('media_name')} ({media.get('media_rel')[:4]})"
                            + (
                                f" 第 {media.get('tv_season')} 季 | 第 {media.get('tv_episode_range')} 集 (共{media.get('tv_episode_count')}集)"
                                if media.get("tv_episode_merged")
                                else (
                                    f" 第 {media.get('tv_season')} 季 | 第 {media.get('tv_episode')} 集"
                                    if media.get("media_type") == "Episode"
                                    else ""
                                )
                            ),
                "description" : f"{media.get('media_intro')}",
                "url" : f"{media.get('media_tmdburl')}",
                "picurl" : f"{media.get('media_backdrop') if media.get('media_type') == 'Movie' else media.get('media_still')}"
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
        episode_info = ""
        if media.get("tv_episode_merged"):
            episode_info = f" 第 {media.get('tv_season')} 季 | 第 {media.get('tv_episode_range')} 集 (共{media.get('tv_episode_count')}集)"
        elif media.get("media_type") == "Episode":
            episode_info = f" 第 {media.get('tv_season')} 季 | 第 {media.get('tv_episode')} 集"
        
        payload = {
            "title": f"🎬 #{media.get('server_name')} 影视更新",
            "body": f"[{'电影' if media['media_type'] == 'Movie' else '剧集'}] {media['media_name']} ({media['media_rel'][:4]})" + episode_info,
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