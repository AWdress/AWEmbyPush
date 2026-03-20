#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import os
import abc, json, time
import my_utils, tmdb_api, tvdb_api, tgbot
import log
import sender
from sender import Sender
from episode_cache import episode_cache_manager

from datetime import datetime
import threading

# 消息去重：记录最近处理过的消息指纹
_message_fingerprints = {}
_fingerprint_lock = threading.Lock()
MESSAGE_DEDUP_WINDOW = int(os.getenv("MESSAGE_DEDUP_WINDOW", "60"))  # 默认60秒去重窗口


class IMedia(abc.ABC):

    def __init__(self):
        self.info_ = {
            "Name": "abc",
            "Type": "Movie/Episode",
            "PremiereYear": 1970,
            "ProviderIds": {"Tmdb": "123", "Imdb": "456", "Tvdb": "789"},
            "Series": 0,
            "Season": 0,
        }
        self.media_detail_ = {
            "server_type": "Emby/Jellyfin",
            "server_url": "https://emby.example.com",
            "server_name": "My_Emby_Server",
            "server_id": "server_id_123",
            "media_id": "item_id_123",
            "media_name": "movie_name",
            "media_type": "Movie/Episode",
            "media_rating": 0.0,
            "media_rel": "1970-01-01",
            "media_intro": "This is a movie/episode introduction.",
            "media_tmdburl": "https://www.themoviedb.org/movie(tv)/123456?language=zh-CN",
            "media_poster": "https://image.tmdb.org/t/p/w500/sFeFWK3SI662yC2sx4clmWttWVj.jpg",
            "media_backdrop": "https://image.tmdb.org/t/p/w500/sFeFWK3SI662yC2sx4clmWttWVj.jpg",
            "media_still": "https://image.tmdb.org/t/p/w500/sFeFWK3SI662yC2sx4clmWttWVj.jpg",
            "tv_season": 0,
            "tv_episode": 0,
            "tv_episode_name": "episode_name",
        }
        self.poster_ = ""
        self.server_name_ = ""
        self.escape_ch = ["_", "*", "`", "["]

    @abc.abstractmethod
    def parse_info(self, emby_media_info):
        pass

    @abc.abstractmethod
    def get_details(self):
        pass

    @abc.abstractmethod
    def send_caption(self):
        pass

    def _get_id(self):
        log.logger.info(json.dumps(self.info_, ensure_ascii=False))
        medias, err = tmdb_api.search_media(
            self.info_["Type"], self.info_["Name"], self.info_["PremiereYear"]
        )
        if err:
            log.logger.error(err)
            return
        Tvdb_id = self.info_["ProviderIds"].get("Tvdb", "-1")
        for m in medias:
            ext_ids, err = tmdb_api.get_external_ids(self.info_["Type"], m["id"])
            if err:
                log.logger.warning(err)
                continue
            if Tvdb_id == str(ext_ids.get("tvdb_id")):
                self.info_["ProviderIds"]["Tmdb"] = str(m["id"])
                break
        if "Tmdb" not in self.info_["ProviderIds"]:
            log.logger.warn(f"No matched media found for {self.info_['Name']} {self.info_['PremiereYear']} in TMDB.")
            if len(medias) == 0:
                log.logger.error(f"No search results found for {self.info_['Name']} {self.info_['PremiereYear']} in TMDB. Cannot proceed.")
                raise Exception(f"No TMDB results found for {self.info_['Name']}")
            # Use first search result as fallback
            if self.info_["Type"] == "Movie":
                log.logger.warn(f"Use the first search result: {medias[0]['title']} {medias[0]['release_date'][:4]}.")
            else:
                log.logger.warn(f"Use the first search result: {medias[0]['original_name']} {medias[0]['first_air_date'][:4]}.")
            self.info_["ProviderIds"]["Tmdb"] = str(medias[0]["id"])


class Movie(IMedia):
    def __init__(self):
        super().__init__()
        self.info_["Type"] = "Movie"

    def __str__(self) -> str:
        return json.dumps(self.info_, ensure_ascii=False)

    def parse_info(self, emby_media_info):
        movie_item = emby_media_info["Item"]
        self.info_["Name"] = movie_item["Name"]
        self.info_["PremiereYear"] = (
            int(movie_item["PremiereDate"])
            if movie_item["PremiereDate"].isdigit()
            else (
                datetime.fromisoformat(
                    movie_item["PremiereDate"].replace("Z", "+00:00")
                ).year
                if my_utils.emby_version_check(emby_media_info["Server"]["Version"])
                else my_utils.iso8601_convert_CST(movie_item["PremiereDate"]).year
            )
        )
        self.info_["ProviderIds"] = movie_item["ProviderIds"]
        self.media_detail_["server_type"] = emby_media_info["Server"]["Type"]
        self.media_detail_["server_name"] = emby_media_info["Server"]["Name"]
        self.media_detail_["server_url"] = emby_media_info["Server"]["Url"]
        self.media_detail_["server_id"] = emby_media_info["Server"].get("Id", "")
        self.media_detail_["media_id"] = movie_item.get("Id", "")
        log.logger.debug(self.info_)

    def send_caption(self):
        # 使用缓存管理器处理推送（支持电视剧集合并）
        episode_cache_manager.add_episode(self.media_detail_)

    def get_details(self):
        if "Tmdb" not in self.info_["ProviderIds"]:
            self._get_id()

        movie_details, err = tmdb_api.get_movie_details(
            self.info_["ProviderIds"]["Tmdb"]
        )
        if err:
            log.logger.error(err)
            raise Exception(err)
        
        poster, err = tmdb_api.get_movie_poster(self.info_["ProviderIds"]["Tmdb"])
        if err:
            log.logger.error(err)
            raise Exception(err)
        
        backdrop, err = tmdb_api.get_movie_backdrop_path(self.info_["ProviderIds"]["Tmdb"])
        if err:
            log.logger.error(err)
            raise Exception(err)

        self.media_detail_["media_name"] = movie_details["title"]
        self.media_detail_["media_type"] = "Movie"
        self.media_detail_["media_rating"] = movie_details["vote_average"]
        self.media_detail_["media_rel"] = movie_details["release_date"]
        self.media_detail_["media_intro"] = movie_details["overview"]
        self.media_detail_["media_tmdbid"] = self.info_["ProviderIds"]["Tmdb"]
        self.media_detail_["media_imdbid"] = self.info_["ProviderIds"].get("Imdb", "")
        self.media_detail_["media_tmdburl"] = f"https://www.themoviedb.org/movie/{self.info_['ProviderIds']['Tmdb']}?language=zh-CN"
        self.media_detail_["media_poster"] = poster
        self.media_detail_["media_backdrop"] = backdrop
        
        # 获取类型信息（genres）
        genres = movie_details.get("genres", [])
        if genres:
            # 取前3个类型并翻译为中文
            genre_names = [tmdb_api.translate_genre(g["name"]) for g in genres[:3]]
            self.media_detail_["media_genres"] = ", ".join(genre_names)
        else:
            self.media_detail_["media_genres"] = "电影"
        
        # 获取演员信息
        cast, err = tmdb_api.get_movie_credits(self.info_["ProviderIds"]["Tmdb"])
        if cast:
            cast_names = [actor["name"] for actor in cast]
            self.media_detail_["media_cast"] = ", ".join(cast_names)
        else:
            log.logger.warning(f"Failed to fetch cast: {err}")
            self.media_detail_["media_cast"] = ""
        
        log.logger.debug(self.media_detail_)


class Episode(IMedia):
    def __init__(self):
        super().__init__()
        self.info_["Type"] = "Episode"

    def __str__(self) -> str:
        return json.dumps(self.info_, ensure_ascii=False)

    def parse_info(self, emby_media_info):
        episode_item = emby_media_info["Item"]
        self.info_["Name"] = episode_item["SeriesName"]
        try:
            self.info_["PremiereYear"] = (
                int(episode_item["PremiereDate"])
                if episode_item["PremiereDate"].isdigit()
                else (
                    datetime.fromisoformat(
                        episode_item["PremiereDate"].replace("Z", "+00:00")
                    ).year
                    if my_utils.emby_version_check(emby_media_info["Server"]["Version"])
                    else my_utils.iso8601_convert_CST(episode_item["PremiereDate"]).year
                )
            )
        except Exception as e:
            log.logger.error(e)
            self.info_["PremiereYear"] = -1
        self.info_["ProviderIds"] = episode_item["ProviderIds"]
        self.info_["Series"] = episode_item["IndexNumber"]
        self.info_["Season"] = episode_item["ParentIndexNumber"]
        self.media_detail_["server_type"] = emby_media_info["Server"]["Type"]
        self.media_detail_["server_name"] = emby_media_info["Server"]["Name"]
        self.media_detail_["server_url"] = emby_media_info["Server"]["Url"]
        self.media_detail_["server_id"] = emby_media_info["Server"].get("Id", "")
        self.media_detail_["media_id"] = episode_item.get("Id", "")
        log.logger.debug(self.info_)

    def get_details(self):
        if "Tvdb" in self.info_["ProviderIds"] and not os.getenv("TVDB_API_KEY") is None:
            tvdb_id, err = tvdb_api.get_seriesid_by_episodeid(self.info_["ProviderIds"]["Tvdb"])
            if err:
                log.logger.warn(err)
                self.info_["ProviderIds"].pop("Tvdb")
            else:
                self.info_["ProviderIds"]["Tvdb"] = str(tvdb_id)

        if "Tmdb" in self.info_["ProviderIds"]:
            # remove
            self.info_["ProviderIds"].pop("Tmdb")

        self._get_id()
        tv_details, err = tmdb_api.get_tv_episode_details(
            self.info_["ProviderIds"]["Tmdb"],
            self.info_["Season"],
            self.info_["Series"],
        )
        if err:
            log.logger.error(err)
            raise Exception(err)
        
        # 获取季度海报
        poster, err = tmdb_api.get_tv_season_poster(
            self.info_["ProviderIds"]["Tmdb"], self.info_["Season"]
        )
        if err:
            log.logger.warning(err)
            log.logger.warning("No season poster found. Try to use TV series main poster.")
            # 降级：使用电视剧主海报
            poster, err = tmdb_api.get_tv_poster(self.info_["ProviderIds"]["Tmdb"])
            if err:
                log.logger.warning(err)
                log.logger.warning("No TV series poster found either. Will use episode still or empty.")
                poster = ""
        
        # 获取剧集剧照
        still, err = tmdb_api.get_tv_episode_still_paths(self.info_["ProviderIds"]["Tmdb"], self.info_["Season"], self.info_["Series"])
        if err:
            log.logger.warning(err)
            if poster:
                log.logger.info("No episode still found. Use poster instead.")
                still = poster
            else:
                log.logger.warning("No still and poster found. Use empty string.")
                still = ""
                poster = ""  # 确保 poster 也有值

        # tv_datails["air_date"] 为 None 时，查询season的air_date
        if tv_details["air_date"] is None:
            log.logger.warning("No air_date found for this episode, will use season air_date.")
            season_details, err = tmdb_api.get_tv_season_details(self.info_["ProviderIds"]["Tmdb"], self.info_["Season"])
            if season_details:
                tv_details["air_date"] = season_details["air_date"]
            else:
                log.logger.error(err)
                log.logger.warning("No air_date found for this episode, will use current year.")
                tv_details["air_date"] = str(datetime.now().year)
        
        # 如果单集简介为空，使用电视剧总简介
        # 同时获取电视剧类型信息（genres）
        episode_overview = tv_details["overview"]
        tv_series_details = None
        
        if not episode_overview or episode_overview.strip() == "":
            log.logger.warning("No episode overview found. Try to use TV series overview.")
            tv_series_details, err = tmdb_api.get_tv_details(self.info_["ProviderIds"]["Tmdb"])
            if err:
                log.logger.warning(err)
                log.logger.warning("No TV series overview found either. Use empty string.")
                episode_overview = ""
            else:
                episode_overview = tv_series_details.get("overview", "")
                log.logger.info("Using TV series overview as fallback.")
        
        # 获取电视剧类型信息（genres）
        if tv_series_details is None:
            tv_series_details, err = tmdb_api.get_tv_details(self.info_["ProviderIds"]["Tmdb"])
        
        if tv_series_details and not err:
            genres = tv_series_details.get("genres", [])
            if genres:
                # 取前3个类型并翻译为中文
                genre_names = [tmdb_api.translate_genre(g["name"]) for g in genres[:3]]
                self.media_detail_["media_genres"] = ", ".join(genre_names)
            else:
                self.media_detail_["media_genres"] = "剧集"
        else:
            log.logger.warning(f"Failed to fetch TV series details for genres: {err}")
            self.media_detail_["media_genres"] = "剧集"
        
        self.media_detail_["media_name"] = self.info_["Name"]
        self.media_detail_["media_type"] = "Episode"
        self.media_detail_["media_tmdbid"] = self.info_["ProviderIds"]["Tmdb"]
        self.media_detail_["media_imdbid"] = self.info_["ProviderIds"].get("Imdb", "")
        # 使用电视剧总评分，而不是单集评分
        if tv_series_details and tv_series_details.get("vote_average"):
            self.media_detail_["media_rating"] = tv_series_details["vote_average"]
        else:
            self.media_detail_["media_rating"] = tv_details["vote_average"]
        self.media_detail_["media_rel"] = tv_details["air_date"]
        self.media_detail_["media_intro"] = episode_overview
        self.media_detail_["media_tmdburl"] = f"https://www.themoviedb.org/tv/{self.info_['ProviderIds']['Tmdb']}?language=zh-CN"
        self.media_detail_["media_poster"] = poster
        self.media_detail_["media_still"] = still
        self.media_detail_["tv_season"] = tv_details["season_number"]
        self.media_detail_["tv_episode"] = tv_details["episode_number"]
        self.media_detail_["tv_episode_name"] = tv_details["name"]
        
        # 获取演员信息
        cast, err = tmdb_api.get_tv_credits(self.info_["ProviderIds"]["Tmdb"])
        if cast:
            cast_names = [actor["name"] for actor in cast]
            self.media_detail_["media_cast"] = ", ".join(cast_names)
        else:
            log.logger.warning(f"Failed to fetch cast: {err}")
            self.media_detail_["media_cast"] = ""
        
        log.logger.debug(self.media_detail_)


    def send_caption(self):
        # 使用缓存管理器处理推送（支持电视剧集合并）
        episode_cache_manager.add_episode(self.media_detail_)


def create_media(emby_media_info):
    if emby_media_info["Item"]["Type"] == "Movie":
        return Movie()
    elif emby_media_info["Item"]["Type"] == "Episode":
        return Episode()
    else:
        raise Exception("Unsupported media type.")


def jellyfin_msg_preprocess(msg):
    # jellyfin msg 部分字段中包含 "\n"，不处理会导致 json.loads() 失败
    if "\n" in msg:
        msg = msg.replace("\n", "")
    original_msg = json.loads(msg)
    # 通过字段 "NotificationType" 判断当前是否为 Jellyfin 事件
    if "NotificationType" in original_msg:
        if original_msg["NotificationType"] != "ItemAdded" or original_msg["ItemType"] not in ["Movie", "Episode"]:
            log.logger.warning(f"Unsupported event type: {original_msg['NotificationType'] or original_msg['ItemType']}")
            return None
        jellyfin_msg = {
            "Title": "event title",
            "Event": "library.new",
            "Item": {
                "Type": "Movie/Episode",
                "Name": "movie name",
                "SeriesName": "series name",
                "PremiereDate": "",
                "IndexNumber": 0,
                "ParentIndexNumber": 0,
                "ProviderIds": {},  # {"Tvdb": "5406258", "Imdb": "tt16116174", "Tmdb": "899082"}
            },
            "Server": {
                "Name": "server name",
                "Type": "Jellyfin",
                "Url": "Jellyfin server url",
            },
        }
        jellyfin_msg["Server"]["Name"] = original_msg["ServerName"]
        jellyfin_msg["Server"]["Type"] = "Jellyfin"
        jellyfin_msg["Server"]["Url"] = original_msg["ServerUrl"]
        jellyfin_msg["Server"]["Id"] = original_msg.get("ServerId", "")
        jellyfin_msg["Event"] = "library.new"

        if original_msg["ItemType"] == "Movie":
            jellyfin_msg["Title"] = f"新 {original_msg['Name']} 在 {original_msg['ServerName']}"
            jellyfin_msg["Item"]["Type"] = "Movie"
            jellyfin_msg["Item"]["Name"] = original_msg["Name"]
            jellyfin_msg["Item"]["Id"] = original_msg.get("ItemId", "")
        elif original_msg["ItemType"] == "Episode":
            jellyfin_msg["Title"] = f"新 {original_msg['SeriesName']} S{original_msg['SeasonNumber00']} - E{original_msg['EpisodeNumber00']} 在 {original_msg['ServerName']}"
            jellyfin_msg["Item"]["Type"] = "Episode"
            jellyfin_msg["Item"]["SeriesName"] = original_msg["SeriesName"]
            jellyfin_msg["Item"]["IndexNumber"] = original_msg["EpisodeNumber"]
            jellyfin_msg["Item"]["ParentIndexNumber"] = original_msg["SeasonNumber"]
            jellyfin_msg["Item"]["Id"] = original_msg.get("ItemId", "")
        else:
            raise Exception("Unsupported media type.")

        jellyfin_msg["Item"]["PremiereDate"] = str(original_msg["Year"])
        if "Provider_tmdb" in original_msg:
            jellyfin_msg["Item"]["ProviderIds"]["Tmdb"] = original_msg["Provider_tmdb"]
        if "Provider_tvdb" in original_msg:
            jellyfin_msg["Item"]["ProviderIds"]["Tvdb"] = original_msg["Provider_tvdb"]
        if "Provider_imdb" in original_msg:
            jellyfin_msg["Item"]["ProviderIds"]["Imdb"] = original_msg["Provider_imdb"]
        # FIXME: Jellyfin 部分剧集没有提供 Provider_imdb 和 Provider_tvdb 信息
        if jellyfin_msg["Item"]["ProviderIds"] == {}:
            log.logger.warning(f"Jellyfin Server not get any ProviderIds for Event: {jellyfin_msg['Title']}")
        return jellyfin_msg
    else:
        original_msg["Server"]["Type"] = "Emby"
        # emby 推送的媒体信息不包含 server url，从环境变量读取或使用默认值
        # 用户可以通过设置 EMBY_SERVER_URL 环境变量来指定自己的 Emby 服务器地址
        original_msg["Server"]["Url"] = os.getenv("EMBY_SERVER_URL", "https://emby.media")
        # Emby 推送消息中包含 Server.Id，但如果缺失则使用 Item.ServerId
        if "Id" not in original_msg["Server"] and "ServerId" in original_msg["Item"]:
            original_msg["Server"]["Id"] = original_msg["Item"]["ServerId"]
        return original_msg


def process_media(emby_media_info):
    emby_media_info = jellyfin_msg_preprocess(emby_media_info)
    if not emby_media_info:
        return
    
    # 生成消息指纹用于去重
    fingerprint = f"{emby_media_info['Title']}_{emby_media_info.get('Event', 'unknown')}"
    current_time = time.time()
    
    with _fingerprint_lock:
        # 清理过期的指纹记录
        expired_keys = [k for k, v in _message_fingerprints.items() if current_time - v > MESSAGE_DEDUP_WINDOW]
        for k in expired_keys:
            del _message_fingerprints[k]
        
        # 检查是否为重复消息
        if fingerprint in _message_fingerprints:
            time_since_last = current_time - _message_fingerprints[fingerprint]
            log.logger.info(
                f"⏭️ 跳过重复消息（{time_since_last:.1f}秒前已处理）: {emby_media_info['Title']}"
            )
            return
        
        # 记录新消息指纹
        _message_fingerprints[fingerprint] = current_time
    
    log.logger.info(f"Received message: {emby_media_info['Title']}")
    if emby_media_info["Event"] != "library.new":
        log.logger.warning(f"Unsupported event type: {emby_media_info['Event']}")
        if emby_media_info["Event"] == "system.notificationtest":
            log.logger.warning("📨 这是一条测试通知消息，请检查您的推送渠道，如果收到消息说明配置成功！")
            sender.Sender.send_test_msg(
                f"🎉 *恭喜！* 🎉 \n\nAWEmbyPush 配置成功！\n\n这是来自 *{emby_media_info['Server']['Name']}* 的测试消息！\n\n现在您可以尝试向 Emby Server 添加新的电影或剧集了~ \n\n发送时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
            )

        return
    try:
        md = create_media(emby_media_info)
        md.parse_info(emby_media_info)
        md.get_details()
        md.send_caption()
    except Exception as e:
        raise e
    else:
        log.logger.info(f"Message processing completed: {emby_media_info['Title']}")
