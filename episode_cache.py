#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import threading
import time
import os
import log
import sender
from typing import Dict, List

# 缓存时间：30秒
CACHE_TIMEOUT = int(os.getenv("EPISODE_CACHE_TIMEOUT", "30"))


class EpisodeCache:
    """电视剧集缓存管理器，用于合并同一电视剧的多集推送"""
    
    def __init__(self):
        self.cache: Dict[str, List[dict]] = {}  # key: tv_show_id, value: [episodes]
        self.timers: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock()
    
    def _get_cache_key(self, media_detail: dict) -> str:
        """生成缓存键：TMDB_ID + 季数"""
        if media_detail.get("media_type") != "Episode":
            return None
        # 使用 TMDB ID + 季数作为唯一标识
        return f"{media_detail.get('media_tmdbid')}_{media_detail.get('tv_season')}"
    
    def _merge_and_send(self, cache_key: str):
        """合并并发送缓存的剧集"""
        with self.lock:
            if cache_key not in self.cache:
                return
            
            episodes = self.cache.pop(cache_key)
            if cache_key in self.timers:
                self.timers.pop(cache_key)
            
            if not episodes:
                return
            
            # 如果只有一集，直接发送
            if len(episodes) == 1:
                log.logger.info(f"📺 发送单集：{episodes[0].get('media_name')} S{episodes[0].get('tv_season')}E{episodes[0].get('tv_episode')}")
                sender.Sender.send_media_details(episodes[0])
                return
            
            # 多集合并发送
            episodes_sorted = sorted(episodes, key=lambda x: x.get('tv_episode', 0))
            first_ep = episodes_sorted[0].get('tv_episode')
            last_ep = episodes_sorted[-1].get('tv_episode')
            
            # 修改第一个媒体信息，将剧集信息改为范围
            merged_media = episodes_sorted[0].copy()
            episode_range = f"{first_ep}-{last_ep}" if first_ep != last_ep else str(first_ep)
            
            # 更新剧集信息显示
            merged_media['tv_episode_merged'] = True
            merged_media['tv_episode_range'] = episode_range
            merged_media['tv_episode_count'] = len(episodes)
            
            log.logger.info(
                f"📺 合并发送 {len(episodes)} 集：{merged_media.get('media_name')} "
                f"S{merged_media.get('tv_season')} 第{episode_range}集"
            )
            
            sender.Sender.send_media_details(merged_media)
    
    def add_episode(self, media_detail: dict):
        """添加剧集到缓存"""
        # 如果不是电视剧，直接发送
        if media_detail.get("media_type") != "Episode":
            log.logger.info(f"🎬 发送电影：{media_detail.get('media_name')}")
            sender.Sender.send_media_details(media_detail)
            return
        
        cache_key = self._get_cache_key(media_detail)
        if not cache_key:
            sender.Sender.send_media_details(media_detail)
            return
        
        with self.lock:
            # 取消现有的定时器
            if cache_key in self.timers:
                self.timers[cache_key].cancel()
            
            # 添加到缓存
            if cache_key not in self.cache:
                self.cache[cache_key] = []
            
            self.cache[cache_key].append(media_detail)
            
            log.logger.info(
                f"📺 缓存剧集：{media_detail.get('media_name')} "
                f"S{media_detail.get('tv_season')}E{media_detail.get('tv_episode')} "
                f"(当前缓存 {len(self.cache[cache_key])} 集)"
            )
            
            # 设置新的定时器
            timer = threading.Timer(CACHE_TIMEOUT, self._merge_and_send, args=[cache_key])
            timer.daemon = True
            timer.start()
            self.timers[cache_key] = timer


# 全局实例
episode_cache_manager = EpisodeCache()

