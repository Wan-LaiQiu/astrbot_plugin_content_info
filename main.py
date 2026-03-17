from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger
from astrbot.api.star import Context, Star, register
import tiktoken
import traceback
import json
import os

@register("context_stat", "WanLaiQiu", "统计当前上下文长度(平衡版)", "3.3.3")
class ContextStatPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoding = None

        self.model_context_limits = self._load_model_config()
        
        # 模型关键词用于初步筛选（更宽松）
        self.model_keywords = [
            'gpt', 'claude', 'kimi', 'deepseek', 'gemini', 'llama', 'qwen', 
            'moonshot', 'o1', 'o3', 'grok', 'mistral', 'mixtral', 'yi',
            'glm', 'chatglm', 'baichuan', 'hunyuan', 'sensechat', 'abab',
            'step', 'command', 'gemma', 'coze', 'azure', 'openai'
        ]
        
        # 缓存
        self._model_cache = {}

    def _load_model_config(self) -> dict:
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "models.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"gpt-4": 8192, "gpt-3.5-turbo": 16384}
        except Exception:
            return {"gpt-4": 8192, "gpt-3.5-turbo": 16384}

    def _is_likely_model_name(self, text: str) -> bool:
        """判断字符串是否可能是模型名称
        标准：包含关键词 + 有数字或连字符 + 长度适中
        """
        if not text or not isinstance(text, str):
            return False
        if len(text) > 100 or len(text) < 3:
            return False
        
        text_lower = text.lower()
        
        # 必须包含至少一个关键词
        has_keyword = any(kw in text_lower for kw in self.model_keywords)
        if not has_keyword:
            return False
        
        # 通常模型名会有数字、连字符或版本号
        has_identifier = any(c.isdigit() for c in text) or '-' in text or '.' in text
        
        return has_identifier

    def _scan_for_model(self, obj, visited=None, depth=0, max_depth=4) -> str:
        """
        递归扫描对象查找模型名
        带循环引用保护和深度限制
        """
        if visited is None:
            visited = set()
        
        obj_id = id(obj)
        if obj_id in visited or depth > max_depth:
            return None
        visited.add(obj_id)
        
        try:
            # 如果是字符串，直接检查
            if isinstance(obj, str):
                if self._is_likely_model_name(obj):
                    return obj
                return None
            
            # 如果是字典
            if isinstance(obj, dict):
                # 优先检查特定 key
                priority_keys = ['model', 'model_name', 'deployment_name', 'engine', 'model_id']
                for key in priority_keys:
                    if key in obj:
                        val = obj[key]
                        if isinstance(val, str) and self._is_likely_model_name(val):
                            return val
                # 递归检查其他值
                for v in obj.values():
                    result = self._scan_for_model(v, visited, depth + 1, max_depth)
                    if result:
                        return result
            
            # 如果是列表/元组
            if isinstance(obj, (list, tuple)):
                for item in obj:
                    result = self._scan_for_model(item, visited, depth + 1, max_depth)
                    if result:
                        return result
            
            # 如果是对象
            if hasattr(obj, '__dict__'):
                # 优先检查常见属性
                priority_attrs = ['model', 'model_name', 'engine', 'deployment_name', 'model_id']
                for attr in priority_attrs:
                    if hasattr(obj, attr):
                        try:
                            val = getattr(obj, attr)
                            if isinstance(val, str) and self._is_likely_model_name(val):
                                return val
                        except:
                            continue
                
                # 检查其他属性（限制数量避免过慢）
                other_attrs = [a for a in dir(obj) if not a.startswith('_') and a not in priority_attrs][:15]
                for attr in other_attrs:
                    try:
                        val = getattr(obj, attr)
                        if not callable(val):
                            result = self._scan_for_model(val, visited, depth + 1, max_depth)
                            if result:
                                return result
                    except:
                        continue
                        
        except Exception:
            pass
        
        return None

    def _probe_model_name(self, conversation, event=None) -> str:
        """
        探测模型名称。
        
        TODO: 待 AstrBot 框架提供标准 API 后迁移。
        当前因框架未暴露统一的 get_model_name() 接口，
        且各 Provider 模型信息存储位置不一致，故采用启发式扫描作为临时方案。
        已添加 depth/visited 等防护措施确保稳定性。
        """
        
        # 快速路径 1：直接属性
        quick_targets = []
        if event:
            quick_targets.append((event, "event"))
            if hasattr(event, 'provider') and event.provider:
                quick_targets.append((event.provider, "event.provider"))
        if conversation:
            quick_targets.append((conversation, "conversation"))
        
        for target, name in quick_targets:
            for attr in ['model', 'model_name', 'engine', 'deployment_name']:
                if hasattr(target, attr):
                    try:
                        val = getattr(target, attr)
                        if isinstance(val, str) and val:
                            if self._is_likely_model_name(val):
                                return val
                            # 即使不符合模式，如果是非空字符串也试试
                            if len(val) < 50 and not val.startswith('<'):
                                return val
                    except:
                        continue
        
        # 递归扫描
        scan_targets = []
        if event:
            scan_targets.append(event)
        if conversation:
            scan_targets.append(conversation)
        
        # Provider Manager
        try:
            pm = getattr(self.context, 'provider_manager', None)
            if pm:
                scan_targets.append(pm)
        except:
            pass
        
        # Context
        if hasattr(self.context, 'provider') and self.context.provider:
            scan_targets.append(self.context.provider)
        
        for target in scan_targets:
            result = self._scan_for_model(target)
            if result:
                return result
        
        return "未知模型"

    async def _get_active_token_limit(self, conversation, event=None, umo=None) -> tuple:
        """获取 (Token上限, 模型名称)"""
        
        # 检查缓存
        if umo and umo in self._model_cache:
            detected_model = self._model_cache[umo]
        else:
            detected_model = self._probe_model_name(conversation, event)
            if umo and detected_model != "未知模型":
                self._model_cache[umo] = detected_model
        
        # 手动配置
        try:
            custom_limit = await self.get_kv_data("custom_max_tokens")
            custom_model = await self.get_kv_data("custom_model_name")
            
            if custom_limit:
                limit_val = int(custom_limit)
                name_val = str(custom_model) if custom_model else detected_model
                display_name = f"{name_val} (手动限额)" if name_val != "未知模型" else "自定义配置"
                return limit_val, display_name
        except Exception:
            pass

        # 匹配 models.json
        if detected_model != "未知模型":
            lower_model = detected_model.lower()
            
            if lower_model in self.model_context_limits:
                return self.model_context_limits[lower_model], detected_model
                
            sorted_keys = sorted(self.model_context_limits.keys(), key=len, reverse=True)
            for key in sorted_keys:
                if key in lower_model:
                    return self.model_context_limits[key], detected_model
                    
        display_name = f"{detected_model} (默认8K)" if detected_model != "未知模型" else "未知模型 (默认8K)"
        return 8192, display_name

    @filter.command("context_limit")
    async def set_context_limit(self, event: AstrMessageEvent, limit_str: str, custom_model: str = ""):
        '''手动覆盖配置，支持绑定模型名: /context_limit 128000 kimi-k2.5'''
        try:
            limit = int(limit_str)
            if limit <= 0 or limit > 10000000:
                yield event.plain_result("❌ 上限值必须在 1 到 10,000,000 之间。")
                return
            await self.put_kv_data("custom_max_tokens", limit)
            
            if custom_model:
                await self.put_kv_data("custom_model_name", custom_model)
                self._model_cache[event.unified_msg_origin] = custom_model
                msg = f"✅ 成功设定: 上限 {limit:,} Tokens\n🤖 已绑定: {custom_model}"
            else:
                msg = f"✅ 成功设定: 上限 {limit:,} Tokens"
                
            yield event.plain_result(msg)
        except ValueError:
            yield event.plain_result("❌ 格式错误。用法: /context_limit <数字> [可选模型名]\n示例: /context_limit 128000 gpt-4o")
        except Exception as e:
            yield event.plain_result(f"❌ 设置失败: {str(e)}")

    @filter.command("context")
    async def get_context_len(self, event: AstrMessageEvent):
        '''使用 /context 指令获取当前上下文统计'''
        try:
            umo = event.unified_msg_origin
            cid = await self.context.conversation_manager.get_curr_conversation_id(umo)
            
            if not cid:
                yield event.plain_result("📭 当前没有开启中的对话。")
                return
                
            conversation = await self.context.conversation_manager.get_conversation(umo, cid)
            
            if not conversation or not conversation.history:
                yield event.plain_result("📭 当前会话没有历史上下文记录。")
                return

            MAX_TOKENS, model_name = await self._get_active_token_limit(conversation, event, umo)

            raw_history = conversation.history
            if isinstance(raw_history, str):
                try:
                    history = json.loads(raw_history)
                except Exception:
                    history = []
            elif isinstance(raw_history, list):
                history = raw_history
            else:
                history = []
                
            if not history:
                yield event.plain_result("📭 当前会话历史记录为空。")
                return

            char_count = 0
            token_count = 0
            msg_count = len(history)

            for msg in history:
                if isinstance(msg, dict):
                    raw_content = msg.get("content", "")
                else:
                    raw_content = getattr(msg, 'content', "")

                text_content = ""
                if isinstance(raw_content, str):
                    text_content = raw_content
                elif isinstance(raw_content, list):
                    for item in raw_content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content += item.get("text", "")
                else:
                    text_content = str(raw_content)
                
                if text_content:
                    char_count += len(text_content)
                    if self.encoding:
                        token_count += len(self.encoding.encode(text_content))

            if self.encoding:
                ratio = (token_count / MAX_TOKENS) * 100
                clamped_ratio = min(ratio, 100.0)
                
                bar_length = 20
                filled_length = int(bar_length * clamped_ratio // 100)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                token_display = f"当前使用: {token_count:,} tokens / {MAX_TOKENS:,} tokens\n{bar}  约 {ratio:.1f}%"
            else:
                token_display = "当前使用: tiktoken未安装"

            result = (
                f"📊 **上下文统计**\n"
                f"--------------------\n"
                f"🤖 模型：{model_name}\n"
                f"💬 消息：{msg_count} 条\n"
                f"📝 字符：{char_count:,} 字\n"
                f"{token_display}\n"
                f"--------------------"
            )
            
            yield event.plain_result(result)

        except Exception as e:
            error_msg = f"统计错误: {str(e)}"
            logger.error(f"统计错误: {traceback.format_exc()}") 
            yield event.plain_result(error_msg)
