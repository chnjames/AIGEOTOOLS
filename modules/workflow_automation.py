"""
智能工作流自动化模块
支持自定义工作流、批量处理、条件触发等功能
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import traceback


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    PAUSED = "paused"  # 已暂停
    CANCELLED = "cancelled"  # 已取消


class WorkflowStep(Enum):
    """工作流步骤类型"""
    KEYWORD_GENERATION = "keyword_generation"  # 关键词生成
    CONTENT_CREATION = "content_creation"  # 内容创作
    CONTENT_OPTIMIZATION = "content_optimization"  # 内容优化
    VERIFICATION = "verification"  # 验证
    CONDITIONAL_CHECK = "conditional_check"  # 条件检查


class WorkflowExecutor:
    """工作流执行引擎"""
    
    def __init__(self, storage, config: Dict[str, Any], callbacks: Optional[Dict[str, Callable]] = None):
        """
        Args:
            storage: DataStorage 实例
            config: 工作流配置
            callbacks: 功能回调函数字典，包含：
                - generate_keywords: 生成关键词的函数
                - generate_content: 生成内容的函数
                - optimize_content: 优化内容的函数
                - verify_keywords: 验证关键词的函数
        """
        self.storage = storage
        self.config = config
        self.workflow_id = config.get("id")
        self.workflow_name = config.get("name", "未命名工作流")
        self.steps = config.get("steps", [])
        self.status = WorkflowStatus.PENDING
        self.current_step_index = 0
        self.execution_log = []
        self.results = {}
        self.error_message = None
        self.callbacks = callbacks or {}
        
    def log(self, message: str, level: str = "info"):
        """记录执行日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "step_index": self.current_step_index
        }
        self.execution_log.append(log_entry)
        print(f"[{level.upper()}] {message}")
    
    def execute_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤"""
        step_type = step.get("type")
        step_name = step.get("name", step_type)
        
        self.log(f"执行步骤: {step_name}")
        
        try:
            if step_type == WorkflowStep.KEYWORD_GENERATION.value:
                return self._execute_keyword_generation(step, context)
            elif step_type == WorkflowStep.CONTENT_CREATION.value:
                return self._execute_content_creation(step, context)
            elif step_type == WorkflowStep.CONTENT_OPTIMIZATION.value:
                return self._execute_content_optimization(step, context)
            elif step_type == WorkflowStep.VERIFICATION.value:
                return self._execute_verification(step, context)
            elif step_type == WorkflowStep.CONDITIONAL_CHECK.value:
                return self._execute_conditional_check(step, context)
            else:
                raise ValueError(f"未知的步骤类型: {step_type}")
        except Exception as e:
            self.log(f"步骤执行失败: {str(e)}", "error")
            raise
    
    def _execute_keyword_generation(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行关键词生成步骤"""
        num_keywords = step.get("params", {}).get("num_keywords", 10)
        generation_mode = step.get("params", {}).get("generation_mode", "AI生成")
        brand = context.get("brand", "")
        advantages = context.get("advantages", "")
        
        self.log(f"生成 {num_keywords} 个关键词（模式: {generation_mode}）")
        
        # 如果有回调函数，使用回调函数生成关键词
        if "generate_keywords" in self.callbacks:
            try:
                keywords = self.callbacks["generate_keywords"](
                    num_keywords=num_keywords,
                    generation_mode=generation_mode,
                    brand=brand,
                    advantages=advantages
                )
                # 保存关键词到数据库
                if keywords:
                    self.storage.save_keywords(keywords, brand)
            except Exception as e:
                self.log(f"关键词生成失败: {str(e)}", "error")
                keywords = []
        else:
            # 如果没有回调函数，返回占位符（用于测试）
            keywords = [f"关键词{i+1}" for i in range(num_keywords)]
        
        return {
            "keywords": keywords,
            "count": len(keywords),
            "generation_mode": generation_mode
        }
    
    def _execute_content_creation(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行内容创作步骤"""
        platforms = step.get("params", {}).get("platforms", [])
        keywords = context.get("keywords", [])
        brand = context.get("brand", "")
        advantages = context.get("advantages", "")
        
        self.log(f"为 {len(keywords)} 个关键词生成内容（平台: {', '.join(platforms)}）")
        
        # 如果有回调函数，使用回调函数生成内容
        if "generate_content" in self.callbacks:
            try:
                contents = []
                for keyword in keywords:
                    for platform in platforms:
                        content = self.callbacks["generate_content"](
                            keyword=keyword,
                            platform=platform,
                            brand=brand,
                            advantages=advantages
                        )
                        if content:
                            contents.append({
                                "keyword": keyword,
                                "platform": platform,
                                "content": content
                            })
                            # 保存内容到数据库
                            self.storage.save_article(keyword, platform, content, f"{keyword}_{platform}.md", brand)
            except Exception as e:
                self.log(f"内容生成失败: {str(e)}", "error")
                contents = []
        else:
            # 如果没有回调函数，返回占位符（用于测试）
            contents = []
            for keyword in keywords:
                for platform in platforms:
                    contents.append({
                        "keyword": keyword,
                        "platform": platform,
                        "content": f"{platform} 内容: {keyword}"
                    })
        
        return {
            "contents": contents,
            "count": len(contents)
        }
    
    def _execute_content_optimization(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行内容优化步骤"""
        platform = step.get("params", {}).get("platform", "通用优化")
        contents = context.get("contents", [])
        
        self.log(f"优化 {len(contents)} 个内容（平台: {platform}）")
        
        # 实际实现中，这里应该调用 geo_tool.py 中的内容优化逻辑
        optimized = []
        for content in contents:
            optimized.append({
                **content,
                "optimized": True,
                "optimization_platform": platform
            })
        
        return {
            "optimized_contents": optimized,
            "count": len(optimized)
        }
    
    def _execute_verification(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行验证步骤"""
        keywords = context.get("keywords", [])
        verify_models = step.get("params", {}).get("verify_models", [])
        max_keywords = step.get("params", {}).get("max_keywords", 20)
        brand = context.get("brand", "")
        advantages = context.get("advantages", "")
        
        keywords_to_verify = keywords[:max_keywords]
        
        self.log(f"验证 {len(keywords_to_verify)} 个关键词（模型: {', '.join(verify_models)}）")
        
        # 如果有回调函数，使用回调函数进行验证
        if "verify_keywords" in self.callbacks:
            try:
                results = self.callbacks["verify_keywords"](
                    keywords=keywords_to_verify,
                    verify_models=verify_models,
                    brand=brand,
                    advantages=advantages
                )
                # 保存验证结果到数据库
                if results:
                    verify_results_list = []
                    for result in results:
                        verify_results_list.append({
                            "query": result.get("keyword", ""),
                            "brand": brand,
                            "verify_model": result.get("model", ""),
                            "mention_count": result.get("mention_count", 0),
                            "mention_position": result.get("mention_position", "")
                        })
                    self.storage.save_verify_results(verify_results_list)
            except Exception as e:
                self.log(f"验证失败: {str(e)}", "error")
                results = []
        else:
            # 如果没有回调函数，返回占位符（用于测试）
            results = []
            for keyword in keywords_to_verify:
                for model in verify_models:
                    results.append({
                        "keyword": keyword,
                        "model": model,
                        "mention_count": 1,
                        "mention_position": "开头"
                    })
        
        return {
            "verify_results": results,
            "count": len(results)
        }
    
    def _execute_conditional_check(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行条件检查步骤"""
        condition_type = step.get("params", {}).get("condition_type")
        threshold = step.get("params", {}).get("threshold", 0.5)
        action = step.get("params", {}).get("action", "skip")
        
        self.log(f"检查条件: {condition_type} (阈值: {threshold})")
        
        # 检查提及率
        if condition_type == "mention_rate":
            verify_results = context.get("verify_results", [])
            if verify_results:
                # 计算平均提及率
                total = len(verify_results)
                mentioned = sum(1 for r in verify_results if r.get("mention_count", 0) > 0)
                mention_rate = mentioned / total if total > 0 else 0
                
                condition_met = mention_rate < threshold
                self.log(f"提及率: {mention_rate:.2%}, 阈值: {threshold:.2%}, 条件满足: {condition_met}")
                
                return {
                    "condition_met": condition_met,
                    "mention_rate": mention_rate,
                    "threshold": threshold,
                    "action": action if condition_met else "continue"
                }
        
        return {
            "condition_met": False,
            "action": "continue"
        }
    
    def execute(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行完整工作流"""
        if context is None:
            context = {}
        
        self.status = WorkflowStatus.RUNNING
        self.log(f"开始执行工作流: {self.workflow_name}")
        
        try:
            for i, step in enumerate(self.steps):
                self.current_step_index = i
                
                # 执行步骤
                step_result = self.execute_step(step, context)
                
                # 将步骤结果合并到上下文中
                context.update(step_result)
                self.results[f"step_{i}"] = step_result
                
                # 检查条件步骤
                if step.get("type") == WorkflowStep.CONDITIONAL_CHECK.value:
                    if step_result.get("condition_met"):
                        action = step_result.get("action", "skip")
                        if action == "skip":
                            self.log("条件满足，跳过后续步骤")
                            break
                        elif action == "retry":
                            self.log("条件满足，重新执行工作流")
                            # 可以在这里实现重试逻辑
                
                self.log(f"步骤 {i+1}/{len(self.steps)} 完成")
            
            self.status = WorkflowStatus.COMPLETED
            self.log("工作流执行完成")
            
            return {
                "status": "success",
                "results": self.results,
                "context": context,
                "log": self.execution_log
            }
            
        except Exception as e:
            self.status = WorkflowStatus.FAILED
            self.error_message = str(e)
            self.log(f"工作流执行失败: {str(e)}", "error")
            self.log(traceback.format_exc(), "error")
            
            return {
                "status": "failed",
                "error": str(e),
                "log": self.execution_log
            }
    
    def get_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        return {
            "id": self.workflow_id,
            "name": self.workflow_name,
            "status": self.status.value,
            "current_step": self.current_step_index,
            "total_steps": len(self.steps),
            "error": self.error_message,
            "log": self.execution_log[-10:] if self.execution_log else []  # 最近10条日志
        }


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self, storage):
        self.storage = storage
    
    def create_workflow(self, name: str, steps: List[Dict[str, Any]], 
                       schedule: Optional[Dict[str, Any]] = None,
                       conditions: Optional[List[Dict[str, Any]]] = None) -> str:
        """创建工作流"""
        workflow = {
            "name": name,
            "steps": steps,
            "schedule": schedule or {},
            "conditions": conditions or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "enabled": True
        }
        
        workflow_id = self.storage.save_workflow(workflow)
        return workflow_id
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流"""
        return self.storage.get_workflow(workflow_id)
    
    def list_workflows(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        return self.storage.list_workflows(enabled_only=enabled_only)
    
    def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> bool:
        """更新工作流"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        workflow.update(updates)
        workflow["updated_at"] = datetime.now().isoformat()
        
        return self.storage.update_workflow(workflow_id, workflow)
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        return self.storage.delete_workflow(workflow_id)
    
    def execute_workflow(self, workflow_id: str, context: Optional[Dict[str, Any]] = None, 
                        callbacks: Optional[Dict[str, Callable]] = None) -> Dict[str, Any]:
        """执行工作流"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {"status": "error", "message": "工作流不存在"}
        
        executor = WorkflowExecutor(self.storage, workflow, callbacks=callbacks)
        result = executor.execute(context)
        
        # 保存执行记录
        execution_record = {
            "workflow_id": workflow_id,
            "status": executor.status.value,
            "result": result,
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat() if executor.status == WorkflowStatus.COMPLETED else None,
            "error": executor.error_message
        }
        
        self.storage.save_workflow_execution(execution_record)
        
        return result
    
    def get_workflow_templates(self) -> List[Dict[str, Any]]:
        """获取工作流模板"""
        return self.storage.get_workflow_templates()
    
    def save_workflow_template(self, name: str, description: str, 
                               steps: List[Dict[str, Any]]) -> str:
        """保存工作流模板"""
        template = {
            "name": name,
            "description": description,
            "steps": steps,
            "created_at": datetime.now().isoformat()
        }
        
        return self.storage.save_workflow_template(template)
    
    def create_workflow_from_template(self, template_id: str, name: str) -> str:
        """从模板创建工作流"""
        template = self.storage.get_workflow_template(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        
        return self.create_workflow(
            name=name,
            steps=template["steps"]
        )
