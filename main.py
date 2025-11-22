#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import asyncio
import log, my_httpd, tmdb_api, tvdb_api, tgbot
import os, time
import sender
from sender import Sender

AUTHOR = "Awhitedress"
VERSION = "4.3.5"
UPDATETIME = "2025-11-22"
DESCRIPTION = "AWEmbyPush 是一个优雅的 Emby/Jellyfin 媒体库更新通知服务"
REPOSITORY = "https://github.com/AWdress/AWEmbyPush"
THANKS_TO = "基于 xu4n_ch3n 的 Emby_Notifier 项目"

WELCOME = f"""
 █████╗ ██╗    ██╗███████╗███╗   ███╗██████╗ ██╗   ██╗██████╗ ██╗   ██╗███████╗██╗  ██╗
██╔══██╗██║    ██║██╔════╝████╗ ████║██╔══██╗╚██╗ ██╔╝██╔══██╗██║   ██║██╔════╝██║  ██║
███████║██║ █╗ ██║█████╗  ██╔████╔██║██████╔╝ ╚████╔╝ ██████╔╝██║   ██║███████╗███████║
██╔══██║██║███╗██║██╔══╝  ██║╚██╔╝██║██╔══██╗  ╚██╔╝  ██╔═══╝ ██║   ██║╚════██║██╔══██║
██║  ██║╚███╔███╔╝███████╗██║ ╚═╝ ██║██████╔╝   ██║   ██║     ╚██████╔╝███████║██║  ██║
╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚═╝     ╚═╝╚═════╝    ╚═╝   ╚═╝      ╚═════╝ ╚══════╝╚═╝  ╚═╝
"""

CONTENT_STR = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🎬 欢迎使用 AWEmbyPush 媒体推送服务 🎬                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  👤 作者 (Author)        : {AUTHOR:<50} ║
║  📦 版本 (Version)       : {VERSION:<50} ║
║  📅 更新时间 (Update)     : {UPDATETIME:<50} ║
║  📝 项目描述 (Description): {DESCRIPTION:<36} ║
║  🔗 项目地址 (Repository) : {REPOSITORY:<43} ║
║  🙏 致谢 (Thanks)        : {THANKS_TO:<48} ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  💡 支持推送渠道: Telegram Bot 📱 | 企业微信 💼 | Bark 🔔                      ║
║  ✨ 支持媒体服务: Emby Server 🎞️  | Jellyfin Server 🎥                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""

CONTENT = {
    "content": "欢迎使用 AWEmbyPush!",
    "作者": AUTHOR,
    "版本": VERSION,
    "更新时间": UPDATETIME,
    "项目描述": DESCRIPTION,
    "项目地址": REPOSITORY,
}


def welcome():
    print("\033[1;32m")
    print(WELCOME)
    print(f"\n{CONTENT_STR}")
    print("\033[0m")

def env_check():
    print(f"{'🔍 正在检查环境变量配置...':<40}")
    print("\n━━━━━━━━ 📊 媒体数据库配置 ━━━━━━━━")
    print(f"{'TMDB_API_TOKEN:':<25} {'[必需]':<8} {os.getenv('TMDB_API_TOKEN', '❌ 未配置')}")
    print(f"{'TMDB_API_HOST:':<25} {'[可选]':<8} {os.getenv('TMDB_API_HOST', 'https://api.themoviedb.org')}")
    print(f"{'TMDB_IMAGE_DOMAIN:':<25} {'[可选]':<8} {os.getenv('TMDB_IMAGE_DOMAIN', 'https://image.tmdb.org')}")
    print(f"{'TVDB_API_KEY:':<25} {'[可选]':<8} {os.getenv('TVDB_API_KEY', '⚪ 未配置')}")
    print("\n━━━━━━━━ 📱 Telegram Bot 配置 ━━━━━━━━")
    print(f"{'TG_BOT_TOKEN:':<25} {'[可选]':<8} {os.getenv('TG_BOT_TOKEN', '⚪ 未配置')}")
    print(f"{'TG_CHAT_ID:':<25} {'[可选]':<8} {os.getenv('TG_CHAT_ID', '⚪ 未配置')}")
    print(f"{'TG_API_HOST:':<25} {'[可选]':<8} {os.getenv('TG_API_HOST', 'https://api.telegram.org')}")
    print("\n━━━━━━━━ 💼 企业微信配置 ━━━━━━━━")
    print(f"{'WECHAT_CORP_ID:':<25} {'[可选]':<8} {os.getenv('WECHAT_CORP_ID', '⚪ 未配置')}")
    print(f"{'WECHAT_CORP_SECRET:':<25} {'[可选]':<8} {os.getenv('WECHAT_CORP_SECRET', '⚪ 未配置')}")
    print(f"{'WECHAT_AGENT_ID:':<25} {'[可选]':<8} {os.getenv('WECHAT_AGENT_ID', '⚪ 未配置')}")
    print(f"{'WECHAT_USER_ID:':<25} {'[可选]':<8} {os.getenv('WECHAT_USER_ID', '@all')}")
    print(f"{'WECHAT_PROXY_URL:':<25} {'[可选]':<8} {os.getenv('WECHAT_PROXY_URL', 'https://qyapi.weixin.qq.com')}")
    print("\n━━━━━━━━ 🔔 Bark 推送配置 ━━━━━━━━")
    print(f"{'BARK_SERVER:':<25} {'[可选]':<8} {os.getenv('BARK_SERVER', 'https://api.day.app')}")
    print(f"{'BARK_DEVICE_KEYS:':<25} {'[可选]':<8} {os.getenv('BARK_DEVICE_KEYS', '⚪ 未配置')}")
    print("\n━━━━━━━━ 📝 日志配置 ━━━━━━━━")
    print(f"{'LOG_LEVEL:':<25} {'[可选]':<8} {os.getenv('LOG_LEVEL', 'INFO')}")
    print(f"{'LOG_EXPORT:':<25} {'[可选]':<8} {os.getenv('LOG_EXPORT', 'False')}")
    print(f"{'LOG_PATH:':<25} {'[可选]':<8} {os.getenv('LOG_PATH', '/var/tmp/awembypush')}")
    print("\n━━━━━━━━ ⚙️  高级配置 ━━━━━━━━")
    print(f"{'EPISODE_CACHE_TIMEOUT:':<25} {'[可选]':<8} {os.getenv('EPISODE_CACHE_TIMEOUT', '30')}秒")

    # 检查媒体数据库信息
    try:
        if os.getenv('TMDB_API_TOKEN') is None:
            raise Exception("❌ TMDB_API_TOKEN 是必需的配置项！")
        if os.getenv('TG_BOT_TOKEN') is None and os.getenv('WECHAT_CORP_ID') is None and os.getenv('BARK_DEVICE_KEYS') is None:
            raise Exception("❌ 至少需要配置一种推送方式：Telegram Bot、企业微信 或 Bark")
        if os.getenv('TG_BOT_TOKEN') and os.getenv('TG_CHAT_ID') is None:
            raise Exception("❌ 配置了 TG_BOT_TOKEN 后，TG_CHAT_ID 也是必需的！")
        if os.getenv('WECHAT_CORP_ID') and (os.getenv('WECHAT_CORP_SECRET') is None or os.getenv('WECHAT_AGENT_ID') is None):
            raise Exception("❌ 企业微信配置不完整，请检查 WECHAT_CORP_SECRET 和 WECHAT_AGENT_ID")
        if os.getenv('BARK_SERVER') and os.getenv('BARK_DEVICE_KEYS') is None:
            raise Exception("❌ 配置了 BARK_SERVER 后，BARK_DEVICE_KEYS 也是必需的！")
    except Exception as e:
        log.logger.error(e)
        print("\033[1;31m")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("❌ 配置错误！请检查并设置必需的环境变量后重启服务！")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("\033[0m")
        while True:
            time.sleep(1)

    if 'True' == os.getenv('LOG_EXPORT'):
        # 如果有日志文件输出，则向日志文件输出欢迎信息
        file_path = os.getenv('LOG_PATH', '/var/tmp/awembypush/') + '/' + time.strftime("%Y-%m-%d", time.localtime()) + '.log'
        print(f"{WELCOME}\n{CONTENT_STR}", file=open(file_path, 'w'))
            

def require_check():
    log.logger.info("🔍 正在检查必需配置的有效性...")
    try:
        # check TMDB_API_TOKEN valid
        log.logger.info("✓ 正在验证 TMDB_API_TOKEN...")
        tmdb_api.login()
        
        # check TG_BOT_TOKEN valid and # check TG_CHAT_ID valid
        if os.getenv('TG_BOT_TOKEN') or os.getenv('TG_CHAT_ID'):
            log.logger.info("✓ 正在验证 Telegram Bot 配置...")
            tgbot.bot_authorization()
            log.logger.info("✓ 正在验证 TG_CHAT_ID...")
            tgbot.get_chat()
        else:
            log.logger.warning("⚠️ 未配置 Telegram Bot")

        # send welcome message
        print("\n" + "="*80)
        print("✅ 配置验证通过！正在初始化推送服务...")
        print("="*80 + "\n")
        
        global Sender
        sender.Sender = sender.SenderManager()
        sender.Sender.send_welcome(CONTENT)

    except Exception as e:
        log.logger.error(e)
        raise e



# 运行主事件循环
if __name__ == "__main__":
    welcome()
    env_check()
    require_check()
    asyncio.run(my_httpd.my_httpd())
