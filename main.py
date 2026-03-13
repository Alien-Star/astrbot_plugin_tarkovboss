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
        '''格式化BOSS数据'''
        try:
            if not data.get("data", {}).get("maps"):
                return "❌ 没有获取到地图数据"
            
            maps = data["data"]["maps"]
            result = ["📊 **塔科夫BOSS刷新率**", "=" * 30]
            
            for map_data in maps:
                map_name = map_data.get("name", "未知地图")
                bosses = map_data.get("bosses", [])
                
                if bosses:
                    result.append(f"\n🗺️ **{map_name}**")
                    for boss in bosses:
                        name = boss.get("name", "未知")
                        chance = boss.get("spawnChance")
                        
                        if chance is None:
                            chance_str = "未知"
                        elif isinstance(chance, (int, float)):
                            if chance <= 1:
                                chance_str = f"{chance*100:.0f}%"
                            else:
                                chance_str = f"{chance:.0f}%"
                        else:
                            chance_str = str(chance)
                        
                        result.append(f"  👾 {name}: {chance_str}")
            
            result.append("\n" + "=" * 30)
            result.append("数据来源: Tarkov API")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ 数据处理错误: {str(e)}"
    
    async def terminate(self):
        pass