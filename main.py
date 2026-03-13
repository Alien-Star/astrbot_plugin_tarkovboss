# main.py
import aiohttp
import json
from typing import Dict, List, Any
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("塔科夫Boss刷率", "AlienStar", "通过API查询塔科夫Boss刷率", "1.0.0")
class TarkovBossAPIPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_url = "https://api.tarkov.dev/graphql"

    @filter.command("boss_debug")
    async def boss_debug(self, event: AstrMessageEvent):
        '''查看API返回的原始BOSS名称'''
        try:
            query = """
            {
            maps {
                name
                bosses {
                name
                }
            }
            }
            """
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json={"query": query}) as resp:
                    data = await resp.json()
                    
                    # 提取所有不重复的BOSS名称
                    boss_names = set()
                    for map_data in data.get("data", {}).get("maps", []):
                        for boss in map_data.get("bosses", []):
                            boss_names.add(boss.get("name", "未知"))
                    
                    # 排序后显示
                    boss_list = sorted(list(boss_names))
                    result = "API返回的BOSS名称列表：\n" + "\n".join(boss_list)
                    yield event.plain_result(result)
        except Exception as e:
            yield event.plain_result(f"调试出错: {str(e)}")
        
    @filter.command("boss")
    async def boss_spawn_api(self, event: AstrMessageEvent):
        '''查询BOSS刷新率（使用API）'''
        # 直接发送结果，不使用图片转换
        try:
            result = await self.fetch_boss_data()
            yield event.plain_result(result)
        except Exception as e:
            logger.error(f"获取BOSS数据失败: {e}")
            yield event.plain_result(f"❌ 获取数据时发生错误: {str(e)}")
    
    async def fetch_boss_data(self) -> str:
        '''从Tarkov API获取BOSS刷新率数据'''
        
        # GraphQL查询语句
        query = """
        {
          maps {
            name
            bosses {
              name
              spawnChance
            }
          }
        }
        """
        
        payload = {"query": query}
        headers = {"Content-Type": "application/json"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return f"❌ API请求失败，状态码: {resp.status}"
                    
                    data = await resp.json()
                    
                    # 检查错误
                    if "errors" in data:
                        return f"❌ API错误: {json.dumps(data['errors'], ensure_ascii=False)}"
                    
                    # 格式化数据
                    return self.format_boss_data(data)
                    
        except asyncio.TimeoutError:
            return "❌ 连接超时，请稍后重试"
        except Exception as e:
            return f"❌ 请求失败: {str(e)}"
    
    def format_boss_data(self, data: Dict) -> str:
        '''格式化BOSS数据为可读文本'''
        try:
            if not data.get("data", {}).get("maps"):
                return "❌ 没有获取到地图数据"
            # 地图名称中英文对照
            map_translation = {
                "Customs": "海关",
                "Woods": "森林", 
                "Lighthouse": "灯塔",
                "Shoreline": "海岸线",
                "Reserve": "储备站",
                "Factory": "工厂",
                "Laboratory": "实验室",
                "Interchange": "立交桥",
                "Streets of Tarkov": "塔科夫街区",
                "Ground Zero": "中心区",
                "The Lab": "实验室",
                "Terminal": "码头"
            }
            # BOSS名称中英文对照
            boss_translation = {
                "Knight": "骑士（三狗之一）",
                "Big Pipe": "大根（三狗之一）",
                "Birdeye": "鸟眼（三狗之一）", 
                "Partisan": "黑老登",
                "Cultist Priest": "邪教徒（祭司）",
                "Cultist": "邪教徒",
                "Smuggler": "走私者小队",
                "Zryachiy": "小鹿",
                "Rogue": "肉鸽",
                "Glukhar": "大锤",
                "Raider": "Raider掠夺者",
                "Reshala": "Re沙拉",
                "Killa": "Killa",
                "Tagilla": "大锤",
                "Shturman": "三枪",
                "Sanitar": "蓝色动力装甲",
                "Kaban": "卡班",
                "Kollontay": "葛朗台",
                "Russian": "俄军",
                "Black Division": "黑色军团",
                "Minotaur": "牛头大锤"
            }



            maps = data["data"]["maps"]
            result = ["📊 **塔科夫BOSS刷新率**", "=" * 35]
            
            # 按地图名称排序
            maps.sort(key=lambda x: x.get("name", ""))
            
            for map_data in maps:
                map_name_en = map_data.get("name", "未知地图")
                # 转换为中文，如果没有对应翻译则保留英文
                map_name_cn = map_translation.get(map_name_en, map_name_en)
                
                bosses = map_data.get("bosses", [])
                
                if bosses:
                    result.append(f"\n🗺️ **{map_name_cn}**")
                    # 按BOSS名称排序
                    bosses.sort(key=lambda x: x.get("name", ""))
                    
                    for boss in bosses:
                        boss_name_en = boss.get("name", "未知BOSS")
                        # 转换为中文
                        boss_name_cn = boss_translation.get(boss_name_en, boss_name_en)
                        
                        spawn_chance = boss.get("spawnChance")
                        
                        # 处理概率值
                        if spawn_chance is None:
                            chance_str = "未知"
                        elif isinstance(spawn_chance, (int, float)):
                            if spawn_chance <= 1:
                                chance_str = f"{spawn_chance*100:.0f}%"
                            else:
                                chance_str = f"{spawn_chance:.0f}%"
                        else:
                            chance_str = str(spawn_chance)
                        
                        result.append(f"  👾 {boss_name_cn}: {chance_str}")
            
            result.append("\n" + "=" * 35)
            result.append("📌 数据来源: Tarkov API | 实时更新")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ 数据处理错误: {str(e)}"
    
    async def terminate(self):
        pass