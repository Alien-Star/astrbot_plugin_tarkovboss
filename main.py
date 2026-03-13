# main.py
import aiohttp
import json
from typing import Dict, List, Any
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("tarkov_boss_api", "你的名字", "通过API查询逃离塔科夫BOSS刷新率", "1.0.0")
class TarkovBossAPIPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_url = "https://api.tarkov.dev/graphql"


    @filter.command("boss_debug")
    async def boss_debug(self, event: AstrMessageEvent):
        '''调试模式：查看API原始返回数据'''
        try:
            async with aiohttp.ClientSession() as session:
                query = "{ maps { name bosses { name spawnChance } } }"
                async with session.post(self.api_url, json={"query": query}) as resp:
                    data = await resp.json()
                    # 返回原始JSON数据的前500个字符
                    result = json.dumps(data, ensure_ascii=False, indent=2)[:500]
                    yield event.plain_result(f"API原始数据:\n{result}")
        except Exception as e:
            yield event.plain_result(f"调试出错: {str(e)}")
        
    @filter.command("boss")
    async def boss_spawn_api(self, event: AstrMessageEvent):
        '''查询BOSS刷新率（使用API）'''
        # 先发送一个等待提示
        yield event.plain_result("🔍 正在从Tarkov API获取BOSS数据，请稍候...")
        
        try:
            result = await self.fetch_boss_data()
            # 直接返回文本，不使用图片转换
            yield event.plain_result(result)
                
        except Exception as e:
            logger.error(f"获取BOSS数据失败: {e}")
            yield event.plain_result(f"❌ 获取数据时发生错误: {str(e)}")
    
    async def fetch_boss_data(self) -> str:
        '''从Tarkov API获取BOSS刷新率数据'''
        
        # GraphQL查询语句 - 简化版本
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
        
        payload = {
            "query": query
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AstrBot-Tarkov-Plugin/1.0"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return f"❌ API请求失败，HTTP状态码: {resp.status}"
                    
                    data = await resp.json()
                    
                    # 检查是否有错误
                    if "errors" in data:
                        errors = data["errors"]
                        return f"❌ GraphQL错误: {json.dumps(errors, ensure_ascii=False)[:200]}"
                    
                    # 解析数据
                    return self.format_boss_data(data)
        except Exception as e:
            return f"❌ 请求API时出错: {str(e)}"
    
    def format_boss_data(self, data: Dict[str, Any]) -> str:
        '''格式化BOSS数据为可读文本'''
        try:
            if not data or "data" not in data or "maps" not in data["data"]:
                return "❌ 返回的数据格式异常"
            
            maps_data = data["data"]["maps"]
            
            if not maps_data:
                return "❌ 没有获取到地图数据"
            
            # 按地图名称排序
            maps_data.sort(key=lambda x: x.get("name", ""))
            
            result_lines = ["📊 **逃离塔科夫BOSS刷新率**", "=" * 30]
            
            boss_count = 0
            for map_item in maps_data:
                map_name = map_item.get("name", "未知地图")
                bosses = map_item.get("bosses", [])
                
                if not bosses:
                    continue
                    
                result_lines.append(f"\n🗺️ **{map_name}**")
                
                # 按BOSS名称排序
                bosses.sort(key=lambda x: x.get("name", ""))
                
                for boss in bosses:
                    boss_name = boss.get("name", "未知BOSS")
                    spawn_chance = boss.get("spawnChance")
                    
                    # 处理可能的None值
                    if spawn_chance is None:
                        chance_str = "未知"
                    elif isinstance(spawn_chance, (int, float)):
                        # 如果返回的是小数（如0.3），转换为百分比
                        if spawn_chance <= 1:
                            chance_str = f"{spawn_chance * 100:.0f}%"
                        else:
                            chance_str = f"{spawn_chance:.0f}%"
                    else:
                        chance_str = str(spawn_chance)
                    
                    result_lines.append(f"  👾 {boss_name}: {chance_str}")
                    boss_count += 1
            
            if boss_count == 0:
                return "❌ 没有找到任何BOSS数据"
            
            result_lines.append("\n" + "=" * 30)
            result_lines.append(f"📌 共 {boss_count} 个BOSS | 数据来源: Tarkov API")
            
            return "\n".join(result_lines)
            
        except Exception as e:
            logger.error(f"格式化数据时出错: {e}")
            return f"❌ 数据处理出错: {str(e)}"
    
    async def terminate(self):
        '''插件卸载时调用'''
        logger.info("Tarkov API插件已卸载")
        pass