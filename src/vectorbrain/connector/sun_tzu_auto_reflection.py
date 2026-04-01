#!/usr/bin/env python3
"""
孙子兵法 + 穷查理宝典 自动反思系统 v2.0

功能：
1. 从群聊记录中自动识别问题/错误/决策场景
2. 用孙子兵法 13 篇 + 穷查理 5 大模型双框架分析
3. 写入反思记忆
4. 发飞书通知

定时执行：每 3 小时
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
import re
import sys
from typing import List, Dict, Tuple

# VectorBrain 路径
VECTORBRAIN_HOME = Path.home() / ".vectorbrain"
COMMON_DIR = VECTORBRAIN_HOME / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from notify_helper import notify_feishu_and_queue, log_event
EPISODIC_DB = VECTORBRAIN_HOME / "memory" / "episodic_memory.db"
REFLECTIONS_DB = VECTORBRAIN_HOME / "reflection" / "reflections.db"
REFLECTION_LOG = VECTORBRAIN_HOME / "auto_reflection" / "logs" / "sun_tzu_reflection.log"

# 孙子兵法 13 篇知识
SUN_TZU_PRINCIPLES = {
    '1_始计篇': {'核心': '谋定而后动', '精髓': '多算胜，少算不胜'},
    '2_作战篇': {'核心': '速战速决', '精髓': '兵贵胜不贵久'},
    '3_谋攻篇': {'核心': '知己知彼', '精髓': '知彼知己百战不殆'},
    '4_军形篇': {'核心': '先为不可胜', '精髓': '先站稳再求胜'},
    '5_兵势篇': {'核心': '出奇制胜', '精髓': '以正合以奇胜'},
    '6_虚实篇': {'核心': '避实击虚', '精髓': '避实击虚'},
    '7_军争篇': {'核心': '以迂为直', '精髓': '以患为利'},
    '8_九变篇': {'核心': '灵活应变', '精髓': '有所不由/不击/不攻'},
    '9_行军篇': {'核心': '观察判断', '精髓': '通过细节看本质'},
    '10_地形篇': {'核心': '因地制宜', '精髓': '知天知地'},
    '11_九地篇': {'核心': '情境领导', '精髓': '切换角色'},
    '12_火攻篇': {'核心': '借势而为', '精髓': '借助外力'},
    '13_用间篇': {'核心': '识人用人', '精髓': '识别贵人小人'}
}

# 穷查理宝典思维模型
MUNGER_MODELS = {
    '逆向思考': {'核心': '反过来想', '精髓': 'Invert, always invert'},
    '能力圈': {'核心': '知道自己不知道什么', '精髓': 'Know the boundaries'},
    '概率思维': {'核心': '期望值决策', '精髓': '概率 × 收益'},
    '第一性原理': {'核心': '回归基本真理', '精髓': '从底层推导'},
    '多元思维': {'核心': '多学科视角', '精髓': 'Latticework of Models'}
}

# 问题识别关键词
PROBLEM_KEYWORDS = [
    # 负面情绪
    '不行', '错了', '错误', '问题', '麻烦', '困难', '头疼', '烦', '担心', '焦虑',
    # 疑问困惑
    '怎么办', '为什么', '怎么', '如何', '要不要', '选哪个', '不知道', '不清楚',
    # 决策点
    '决定', '选择', '考虑', '犹豫', '纠结', '权衡',
    # 冲突分歧
    '不同意', '反对', '矛盾', '冲突', '分歧', '争执',
    # 失败教训
    '失败', '搞砸', '失误', '教训', '后悔', '当初', '早知道'
]

# 飞书配置
FEISHU_CONFIG = {
    'webhook': None,  # 从配置文件读取
    'target_user': 'ou_cd2f520717fd4035c6ef3db89a53b748'  # [YOUR_NAME]
}


class SunTzuReflectionEngine:
    """孙子兵法自动反思引擎"""
    
    def __init__(self):
        self.problem_patterns = self._load_problem_patterns()
        self.reflections = []
        
    def _load_problem_patterns(self) -> Dict:
        """加载问题识别模式"""
        return {
            'decision': {'keywords': ['要不要', '选哪个', '决定', '选择'], 'principle': '1_始计篇'},
            'uncertainty': {'keywords': ['不知道', '不清楚', '怎么办'], 'principle': '3_谋攻篇'},
            'conflict': {'keywords': ['不同意', '反对', '矛盾'], 'principle': '6_虚实篇'},
            'failure': {'keywords': ['失败', '搞砸', '教训'], 'principle': '8_九变篇'},
            'rush': {'keywords': ['快点', '赶紧', '来不及'], 'principle': '2_作战篇'},
            'people': {'keywords': ['这个人', '他怎么', '值得'], 'principle': '13_用间篇'}
        }
    
    def get_recent_conversations(self, hours: int = None, limit: int = 3000) -> List[Dict]:
        """获取对话记录（默认全盘搜索 3000 条）"""
        try:
            conn = sqlite3.connect(EPISODIC_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 获取最近的对话（排除系统消息和图片）
            # 不限制时间，全盘搜索
            cursor.execute("""
                SELECT chat_id, chat_name, sender_id, sender_name, content, timestamp
                FROM conversations
                WHERE msg_type = 'text'
                AND length(content) > 15
                AND content NOT LIKE '%【图片】%'
                AND content NOT LIKE '%【文件】%'
                AND content NOT LIKE '%【表情包】%'
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            conversations = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return conversations
        except Exception as e:
            print(f"⚠️ 读取对话失败：{e}")
            return []
    
    def identify_problems(self, conversations: List[Dict]) -> List[Dict]:
        """从对话中识别问题/决策场景（智能识别）"""
        problems = []
        seen_content = set()  # 避免重复
        
        for conv in conversations:
            content = conv['content']
            
            # 跳过太短或已处理的消息
            if len(content) < 15:
                continue
            if content in seen_content:
                continue
            
            # 智能识别：不仅看关键词，还看上下文
            matched_patterns = []
            
            # 1. 关键词匹配
            for pattern_name, pattern_info in self.problem_patterns.items():
                for keyword in pattern_info['keywords']:
                    if keyword in content:
                        matched_patterns.append({
                            'type': pattern_name,
                            'keyword': keyword,
                            'principle': pattern_info['principle'],
                            'confidence': 0.7
                        })
                        break
            
            # 2. 上下文分析（更智能）
            # 问号 = 疑问/决策
            if '?' in content or '？' in content:
                if any(w in content for w in ['怎么', '为什么', '要不要', '选哪个', '如何']):
                    matched_patterns.append({
                        'type': 'decision_uncertainty',
                        'keyword': '疑问句',
                        'principle': '1_始计篇',
                        'confidence': 0.8
                    })
            
            # 否定词 + 行动 = 困难/阻碍
            if any(w in content for w in ['不', '没', '别', '莫']):
                if any(w in content for w in ['行', '可以', '能', '好', '成']):
                    matched_patterns.append({
                        'type': 'obstacle',
                        'keyword': '否定 + 行动',
                        'principle': '6_虚实篇',
                        'confidence': 0.75
                    })
            
            # 时间词 + 压力 = 速战速决场景
            if any(w in content for w in ['今天', '明天', '快点', '赶紧', '来不及']):
                if any(w in content for w in ['要', '必须', '得', '急']):
                    matched_patterns.append({
                        'type': 'time_pressure',
                        'keyword': '时间压力',
                        'principle': '2_作战篇',
                        'confidence': 0.8
                    })
            
            # 人 + 评价 = 识人场景
            if any(w in content for w in ['他', '她', '这个人', '老板', '供应商', '客户']):
                if any(w in content for w in ['怎么', '为什么', '值得', '靠谱', '行']):
                    matched_patterns.append({
                        'type': 'people_assessment',
                        'keyword': '识人',
                        'principle': '13_用间篇',
                        'confidence': 0.85
                    })
            
            # 如果有匹配，记录为潜在问题（只保留最高置信度）
            if matched_patterns:
                best_match = max(matched_patterns, key=lambda x: x['confidence'])
                if best_match['confidence'] >= 0.6:  # 阈值
                    problems.append({
                        'conversation': conv,
                        'patterns': [best_match],  # 只保留最好的
                        'content_preview': content[:150],
                        'confidence': best_match['confidence']
                    })
                    seen_content.add(content)
        
        # 按置信度排序，优先处理高置信度
        problems.sort(key=lambda x: -x['confidence'])
        
        return problems
    
    def analyze_with_sun_tzu(self, problem: Dict) -> Dict:
        """用孙子兵法分析问题"""
        conv = problem['conversation']
        patterns = problem['patterns']
        
        # 选择最匹配的孙子兵法原则
        best_match = max(patterns, key=lambda x: len(x['keyword']))
        principle_key = best_match['principle']
        principle = SUN_TZU_PRINCIPLES.get(principle_key, {})
        
        # 生成分析
        analysis = self._generate_analysis(conv, principle, patterns)
        
        return {
            'problem': problem,
            'principle': principle,
            'principle_key': principle_key,
            'analysis': analysis
        }
    
    def _generate_analysis(self, conv: Dict, principle: Dict, patterns: List) -> str:
        """生成深度孙子兵法分析"""
        content = conv['content']
        sender = conv['sender_name']
        chat = conv.get('chat_name', 'Unknown')
        pattern = patterns[0] if patterns else {}
        
        analysis = f"""
## 📍 场景还原
**对话者：** {sender}
**群聊/场景：** {chat}
**时间：** {conv.get('timestamp', 'Unknown')}
**原始内容：** {content}

## 🧠 问题识别
**类型：** {pattern.get('type', 'Unknown')}
**识别依据：** {pattern.get('keyword', 'Unknown')}
**置信度：** {pattern.get('confidence', 0) * 100:.0f}%

## 📖 孙子兵法应用
**篇目：** {list(SUN_TZU_PRINCIPLES.keys())[list(SUN_TZU_PRINCIPLES.values()).index(principle)] if principle in SUN_TZU_PRINCIPLES.values() else 'Unknown'}
**核心思想：** {principle.get('核心', 'Unknown')}
**原文精髓：** {principle.get('精髓', 'Unknown')}

## 🔍 深度分析
**为什么会出现这个问题？**
[分析] {self._analyze_root_cause(content, pattern)}

**当时可能忽略了什么？**
[盲点] {self._identify_blind_spot(content, principle)}

**如果用孙子兵法，会怎么做？**
[建议] {self._get_sun_tzu_advice(principle, content, pattern)}

**这个建议的底层逻辑是什么？**
[原理] {self._explain_principle(principle)}

## 💡 可执行建议
1. {self._generate_action_item_1(content, principle)}
2. {self._generate_action_item_2(content, principle)}
3. {self._generate_action_item_3(content, principle)}

## ⚠️ 风险提醒
{self._warn_risks(principle, content)}
"""
        return analysis
    
    def _analyze_root_cause(self, content: str, pattern: Dict) -> str:
        """分析根本原因"""
        ptype = pattern.get('type', '')
        if ptype == 'decision_uncertainty':
            return "信息不足或选项太多，导致无法快速决策"
        elif ptype == 'obstacle':
            return "遇到阻碍，可能是资源不足或方法不对"
        elif ptype == 'time_pressure':
            return "时间规划不足，或低估了任务复杂度"
        elif ptype == 'people_assessment':
            return "对人的了解不够，或缺乏识人框架"
        else:
            return "需要更多上下文分析"
    
    def _identify_blind_spot(self, content: str, principle: Dict) -> str:
        """识别盲点"""
        core = principle.get('核心', '')
        if '谋定' in core:
            return "可能没有充分计算胜率，或只算成功不算失败"
        elif '知己' in core:
            return "可能不了解对方真实需求，或不了解自己的底线"
        elif '速战' in core:
            return "可能拖延太久，或没有设定明确截止日期"
        else:
            return "需要结合具体场景分析"
    
    def _explain_principle(self, principle: Dict) -> str:
        """解释原理"""
        core = principle.get('核心', '')
        if '谋定' in core:
            return "多算胜，少算不胜 — 决策前充分计算，胜率>50%才行动"
        elif '知己' in core:
            return "知彼知己百战不殆 — 信息优势=决策优势"
        elif '速战' in core:
            return "兵贵胜不贵久 — 拖延消耗资源，增加变数"
        elif '避实' in core:
            return "避实击虚 — 不打硬仗，找对手弱点"
        elif '识人' in core:
            return "三军之事莫亲于间 — 识人用人是核心能力"
        else:
            return "孙子兵法强调因势利导，灵活应变"
    
    def _generate_action_item_1(self, content: str, principle: Dict) -> str:
        """生成行动项 1"""
        return "复盘此决策场景，记录当时的思考过程"
    
    def _generate_action_item_2(self, content: str, principle: Dict) -> str:
        """生成行动项 2"""
        return "下次遇到类似情况，先暂停 3 秒，用孙子兵法框架分析"
    
    def _generate_action_item_3(self, content: str, principle: Dict) -> str:
        """生成行动项 3"""
        return "一周后回顾这个决策，验证孙子兵法建议是否有效"
    
    def _warn_risks(self, principle: Dict, content: str) -> str:
        """风险提醒"""
        core = principle.get('核心', '')
        if '谋定' in core:
            return "⚠️ 警惕：过度分析导致拖延，或只算自己不算对手"
        elif '速战' in core:
            return "⚠️ 警惕：为了快而快，没准备好就冲动出击"
        elif '知己' in core:
            return "⚠️ 警惕：只收集信息不分析，或只分析不行动"
        else:
            return "⚠️ 警惕：生搬硬套，不看具体场景"
    
    def _get_sun_tzu_advice(self, principle: Dict, content: str, pattern: Dict) -> str:
        """根据孙子兵法原则给出建议"""
        core = principle.get('核心', '')
        
        if '谋定' in core:
            return "先计算胜率：成功概率多少？最坏情况是什么？能否承受？信息全吗？"
        elif '速战' in core:
            return "设定明确截止日期：什么时候必须完成？拖延的代价是什么？"
        elif '知己' in core:
            return "收集情报：对方想要什么？我的底线是什么？信息对称吗？"
        elif '不可胜' in core:
            return "先站稳脚跟：资金/团队/产品准备好了吗？再求胜机"
        elif '出奇' in core:
            return "寻找差异化：常规做法是什么？意外招数是什么？"
        elif '避实' in core:
            return "找对方弱点：哪里是虚？哪里是实？能否绕开硬仗？"
        elif '识人' in core:
            return "观察行为：他说过什么？做过什么？言行一致吗？"
        else:
            return "灵活应变：当前场景的特殊性是什么？需要调整策略吗？"
    
    def save_reflection(self, analysis_result: Dict) -> str:
        """保存反思到数据库"""
        try:
            conn = sqlite3.connect(REFLECTIONS_DB, timeout=30)
            cursor = conn.cursor()
            
            conv = analysis_result['problem']['conversation']
            principle = analysis_result['principle']
            analysis = analysis_result['analysis']
            
            # 使用唯一 ID（包含时间戳 + 随机数）
            import random
            reflection_id = f"sun_tzu_auto_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
            
            cursor.execute('''
                INSERT INTO reflections 
                (reflection_id, task_id, goal_id, outcome, success, analysis, 
                 lessons_learned, action_items, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reflection_id,
                conv.get('chat_id', 'chat_reflection'),
                None,
                'analyzed',
                1,
                analysis,
                f"孙子兵法{principle.get('核心', '')}应用",
                f"复盘此决策，验证孙子兵法建议",
                'sun_tzu_auto_reflection',
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            return reflection_id
        except Exception as e:
            print(f"⚠️ 保存反思失败：{e}")
            return None
    
    def send_feishu_notification(self, reflections: List[Dict]) -> bool:
        """发送飞书通知"""
        if not reflections:
            return True

        summary = self._generate_summary(reflections)
        notification = {
            "timestamp": datetime.now().isoformat(),
            "type": "sun_tzu_reflection",
            "title": f"孙子兵法自动反思 - {len(reflections)} 条",
            "description": summary[:500],
            "reflections": [
                {
                    "principle": r['principle'].get('核心', ''),
                    "content_preview": r['problem']['content_preview']
                }
                for r in reflections[:10]
            ]
        }

        result = notify_feishu_and_queue(
            summary,
            notification=notification,
            target="user:ou_cd2f520717fd4035c6ef3db89a53b748",
            timeout=60,
            script="sun_tzu_auto_reflection",
        )

        if result["queued"]:
            print(f"✅ 通知已写入：{result['queue_detail']}")
        else:
            print(f"⚠️ 通知队列写入失败：{result['queue_detail']}")

        if result["sent"]:
            print("✅ 飞书通知已发送")
            return True

        print(f"⚠️ 飞书发送失败：{result['send_detail']}")
        return False
    
    def _generate_summary(self, reflections: List[Dict]) -> str:
        """生成反思摘要"""
        summary = f"""🧠 孙子兵法自动反思报告
⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
📊 分析数量：{len(reflections)} 条

"""
        # 按原则分组统计
        principle_count = {}
        for r in reflections:
            key = r['principle'].get('核心', '未知')
            principle_count[key] = principle_count.get(key, 0) + 1
        
        summary += "📈 原则分布：\n"
        for principle, count in sorted(principle_count.items(), key=lambda x: -x[1])[:5]:
            summary += f"  • {principle}: {count}次\n"
        
        summary += "\n💡 详细反思已写入 VectorBrain reflections.db\n"
        
        return summary
    
    def run(self, hours: int = 24, target_reflections: int = 15) -> int:
        """执行自动反思"""
        print("=" * 60)
        print("🧠 孙子兵法自动反思系统")
        print(f"⏰ 时间：{datetime.now().isoformat()}")
        print(f"📊 目标：{target_reflections} 条反思")
        print("=" * 60)
        
        # 1. 获取对话
        print("\n📥 步骤 1: 获取最近对话...")
        conversations = self.get_recent_conversations(hours=hours, limit=200)
        print(f"   获取 {len(conversations)} 条对话")
        
        if not conversations:
            print("   ⚠️ 无对话记录")
            return 0
        
        # 2. 识别问题
        print("\n🔍 步骤 2: 识别问题场景...")
        problems = self.identify_problems(conversations)
        print(f"   识别 {len(problems)} 个潜在问题")
        
        if not problems:
            print("   ⚠️ 无问题场景")
            return 0
        
        # 3. 分析并保存
        print("\n📝 步骤 3: 用孙子兵法分析...")
        saved_count = 0
        for i, problem in enumerate(problems[:target_reflections]):
            analysis = self.analyze_with_sun_tzu(problem)
            reflection_id = self.save_reflection(analysis)
            
            if reflection_id:
                saved_count += 1
                print(f"   ✅ [{saved_count}] {analysis['principle'].get('核心', '')}")
                self.reflections.append(analysis)
        
        # 4. 发送通知
        print("\n📱 步骤 4: 写入通知队列并推送飞书...")
        if self.send_feishu_notification(self.reflections):
            print("   ✅ 通知队列与飞书推送均成功")
        
        # 5. 写日志
        self._write_log(saved_count)
        
        print("\n" + "=" * 60)
        print(f"✅ 完成！生成 {saved_count} 条反思")
        print("=" * 60)
        
        return saved_count
    
    def _write_log(self, count: int):
        """写日志"""
        try:
            REFLECTION_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(REFLECTION_LOG, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} | 生成反思 {count} 条\n")
        except Exception as e:
            print(f"⚠️ 写日志失败：{e}")


def main():
    """主函数"""
    engine = SunTzuReflectionEngine()
    
    # 执行反思（分析最近 24 小时，目标 15 条）
    count = engine.run(hours=24, target_reflections=15)
    
    return 0 if count > 0 else 1


if __name__ == "__main__":
    exit(main())
