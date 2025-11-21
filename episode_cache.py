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

            # 根据集数去重：同一季同一集号如果出现多次，只保留一条
            unique_episodes = {}
            for ep in episodes_sorted:
                ep_num = ep.get('tv_episode')
                if ep_num not in unique_episodes:
                    unique_episodes[ep_num] = ep

            episodes_dedup = [unique_episodes[num] for num in sorted(unique_episodes.keys())]
            episode_numbers = [ep.get('tv_episode') for ep in episodes_dedup]
            first_ep = episode_numbers[0]
            last_ep = episode_numbers[-1]
            
            # 判断剧集是否连续
            is_continuous = all(
                episode_numbers[i] + 1 == episode_numbers[i + 1] 
                for i in range(len(episode_numbers) - 1)
            )
            
            # 修改第一个媒体信息，将剧集信息改为范围或列表
            merged_media = episodes_dedup[0].copy()
            if is_continuous:
                # 连续集数：显示为范围 "1-3"
                episode_range = f"{first_ep}-{last_ep}" if first_ep != last_ep else str(first_ep)
            else:
                # 不连续集数：显示为列表 "1,3,5"
                episode_range = ",".join(str(ep) for ep in episode_numbers)
            
            # 更新剧集信息显示
            merged_media['tv_episode_merged'] = True
            merged_media['tv_episode_range'] = episode_range
            merged_media['tv_episode_count'] = len(episodes_dedup)
            merged_media['tv_episode_continuous'] = is_continuous
            
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

