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
        yield event.plain_result("🔍 正在从Tarkov API获取BOSS数据，请稍候...")
        
        try:
            result = await self.fetch_boss_data()
            
            # 如果结果太长，转换为图片发送（体验更好）
            if len(result) > 500:
                img_path = await self.text_to_image(result)
                yield event.image_result(img_path)
            else:
                yield event.plain_result(result)
                
        except Exception as e:
            logger.error(f"获取BOSS数据失败: {e}")
            yield event.plain_result(f"❌ 获取数据时发生错误: {str(e)[:50]}...")
    
    async def fetch_boss_data(self) -> str:
        '''从Tarkov API获取BOSS刷新率数据'''
        
        # GraphQL查询语句 - 根据API实际结构调整字段名
        query = """
        {
          maps {
            name
            bosses {
              name
              spawnChance
              # 如果有具体刷新点信息，可以取消下面的注释
              # spawnLocations {
              #   name
              #   chance
              # }
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
    
    def format_boss_data(self, data: Dict[str, Any]) -> str:
        '''格式化BOSS数据为可读文本'''
        if not data or "data" not in data or "maps" not in data["data"]:
            return "❌ 返回的数据格式异常"
        
        maps_data = data["data"]["maps"]
        
        # 按地图名称排序
        maps_data.sort(key=lambda x: x.get("name", ""))
        
        result_lines = ["📊 **逃离塔科夫BOSS刷新率**", "=" * 30]
        
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
                # 注意：字段名可能需要根据实际返回结果调整
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
            
            result_lines.append("-" * 20)
        
        # 添加数据来源说明
        result_lines.append("\n📌 数据来源: Tarkov API")
        result_lines.append("🔄 实时更新")
        
        return "\n".join(result_lines)
    
    async def text_to_image(self, text: str) -> str:
        '''将长文本转换为图片（AstrBot内置功能）'''
        try:
            # 使用AstrBot内置的文本转图片功能
            from astrbot.api.message_components import Image
            from astrbot.core.utils.image_table import text_to_image as t2i
            
            img_bytes = await t2i(text, width=800)
            # 保存临时文件
            import tempfile
            import os
            
            fd, path = tempfile.mkstemp(suffix='.png')
            with os.fdopen(fd, 'wb') as f:
                f.write(img_bytes)
            return path
        except Exception as e:
            logger.error(f"文本转图片失败: {e}")
            return None
    
    async def terminate(self):
        '''插件被卸载时调用'''
        logger.info("Tarkov API插件已卸载")
        pass