#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南野科技项目月报 PDF 生成器
使用 macOS 系统中文字体 (STHeiti)
"""
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import os

# 注册中文字体
font_path = "/System/Library/Fonts/STHeiti Light.ttc"
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont('STHeiti', font_path))
    print(f"✓ 中文字体已注册：{font_path}")
else:
    print(f"✗ 字体文件不存在：{font_path}")
    exit(1)

# 文档路径
doc_path = '/home/user/.openclaw/workspace/南野科技项目月报_2026-03-最终版.pdf'
doc = SimpleDocTemplate(doc_path, pagesize=A4, 
                        rightMargin=1.5*cm, leftMargin=1.5*cm,
                        topMargin=2*cm, bottomMargin=2*cm,
                        title="南野科技项目月报")

# 样式 - 使用中文字体
styles = getSampleStyleSheet()
title_style = ParagraphStyle('Title', fontName='STHeiti', fontSize=18, leading=24, spaceAfter=20, alignment=TA_CENTER)
h1_style = ParagraphStyle('H1', fontName='STHeiti', fontSize=14, leading=20, spaceAfter=15, spaceBefore=12, textColor=colors.HexColor('#1a73e8'))
h2_style = ParagraphStyle('H2', fontName='STHeiti', fontSize=11, leading=16, spaceAfter=10, spaceBefore=8)
normal_style = ParagraphStyle('Normal', fontName='STHeiti', fontSize=10, leading=14, spaceAfter=6)
footer_style = ParagraphStyle('Footer', fontName='STHeiti', fontSize=9, leading=12, textColor=colors.grey)

content = []

# ============ 封面 ============
content.append(Paragraph(" ", title_style))
content.append(Paragraph("南野科技", title_style))
content.append(Paragraph("项目组合管理月报", title_style))
content.append(Spacer(1, 1*cm))
content.append(Paragraph("报告周期：2025 年 9 月 - 2026 年 3 月", normal_style))
content.append(Paragraph("生成时间：2026-03-01 01:55", normal_style))
content.append(Paragraph("保密级别：内部机密", normal_style))
content.append(Paragraph("汇报对象：供应链主管 [YOUR_NAME]", normal_style))
content.append(Spacer(1, 0.5*cm))
content.append(Paragraph("_______________________________________", footer_style))
content.append(Spacer(1, 1*cm))

# ============ 执行摘要 ============
content.append(Paragraph("执行摘要 (Executive Summary)", h1_style))

summary_data = [
    ['指标', '数值', '状态'],
    ['活跃项目数', '11', '🟢 正常'],
    ['按期完成率', '76%', '🟡 需关注'],
    ['资源利用率', '78%', '🟢 良好'],
    ['高风险项目', '1', '🟡 需关注'],
    ['暂停项目', '1', 'ℹ️ 蜘蛛侠书包'],
    ['预算执行率', '88%', '🟢 正常'],
]
summary_table = Table(summary_data, colWidths=[5*cm, 3*cm, 4*cm])
summary_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a73e8')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f0f7ff')),
    ('FONTNAME', (0,0), (-1,-1), 'STHeiti'),
    ('FONTSIZE', (0,0), (-1,-1), 10),
]))
content.append(summary_table)
content.append(Spacer(1, 0.3*cm))

content.append(Paragraph("核心洞察：", h2_style))
insights = [
    "📌 蜘蛛侠书包项目已暂停，资源重新分配",
    "📌 女生书包、Switch 书包持续推进中",
    "📌 助理资源（许瑶）可优化配置",
    "📌 婴童类新市场开拓尚未启动，建议加速"
]
for insight in insights:
    content.append(Paragraph(insight, normal_style))
content.append(Spacer(1, 0.5*cm))

# ============ 资源分配 ============
content.append(Paragraph("资源分配矩阵", h1_style))
resource_data = [
    ['成员', '角色', '主责领域', '负载率', '状态'],
    ['[YOUR_NAME]', '供应链主管', '物流/财务/采购', '75%', '🟢'],
    ['徐龙宾', '产品开发', '书包/婴童类', '85%', '🟢'],
    ['卢思圻', '运营', '上架/VAT/财税', '70%', '🟢'],
    ['许瑶', '助理', '协助/文档/测试', '55%', '🟢'],
    ['周凡', '开发/设计', '书包/毛巾', '80%', '🟢'],
    ['张新', '助理', '调研/数据/AI', '60%', '🟢'],
    ['黄宗旨', '设计', '主图/A+/说明书', '85%', '🟢'],
    ['易灵', '助理', '测试/调研', '50%', '🟢'],
    ['陈亮亮', '财务/物流', '银行/社保/ERP', '75%', '🟢'],
]
resource_table = Table(resource_data, colWidths=[2*cm, 2.5*cm, 4*cm, 2*cm, 1.5*cm])
resource_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a73e8')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('FONTNAME', (0,0), (-1,-1), 'STHeiti'),
    ('FONTSIZE', (0,0), (-1,-1), 9),
    ('BACKGROUND', (0,1), (-1,-1), colors.white),
]))
content.append(resource_table)
content.append(Spacer(1, 0.3*cm))
content.append(Paragraph("💡 资源优化：蜘蛛侠暂停后，设计产能已缓解；许瑶可更多参与项目协调", normal_style))
content.append(Spacer(1, 0.5*cm))

# ============ 风险登记册 ============
content.append(Paragraph("风险登记册 (Risk Register)", h1_style))
risk_data = [
    ['ID', '风险描述', '概率', '影响', '风险分', '缓解措施'],
    ['R01', '婴童类市场进入延迟', '中', '中', '6/10', '加速市场调研'],
    ['R02', 'Switch 配色确认延迟', '低', '中', '4/10', '每日跟进确认'],
    ['R03', '莆田银行开户未完成', '中', '低', '3/10', '每周跟进银行'],
]
risk_table = Table(risk_data, colWidths=[1.2*cm, 4*cm, 1.2*cm, 1.2*cm, 1.5*cm, 3.5*cm])
risk_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a73e8')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('FONTNAME', (0,0), (-1,-1), 'STHeiti'),
    ('FONTSIZE', (0,0), (-1,-1), 8),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
]))
content.append(risk_table)
content.append(Spacer(1, 0.2*cm))
content.append(Paragraph("ℹ️ 变更说明：设计资源不足风险已因蜘蛛侠项目暂停而消除", normal_style))
content.append(Spacer(1, 0.5*cm))

# ============ 行动项 ============
content.append(Paragraph("本周行动项 (Action Items)", h1_style))
action_data = [
    ['优先级', '行动项', '负责人', '截止日', '状态'],
    ['P0', 'Switch 透明款配色确认', '[YOUR_NAME]', '03-07', '⏸️ 待决策'],
    ['P1', '女生书包方案完善', '徐龙宾', '03-08', '🟡 进行中'],
    ['P1', '毛巾产品完整上架', '卢思圻', '03-07', '🟡 进行中'],
    ['P1', '莆田银行开户完成', '陈亮亮', '03-10', '🟡 进行中'],
    ['P2', '婴童类市场调研启动', '徐龙宾', '03-15', '⏸️ 未开始'],
    ['P2', '蜘蛛侠项目收尾文档', '周凡', '03-12', '⏸️ 暂停'],
]
action_table = Table(action_data, colWidths=[1.5*cm, 5*cm, 2*cm, 2*cm, 2.5*cm])
action_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a73e8')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ('FONTNAME', (0,0), (-1,-1), 'STHeiti'),
    ('FONTSIZE', (0,0), (-1,-1), 9),
    ('BACKGROUND', (0,1), (0,1), colors.HexColor('#ffeb3b')),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
]))
content.append(action_table)
content.append(Spacer(1, 0.5*cm))

# ============ 管理层决策 ============
content.append(Paragraph("管理层决策需求", h1_style))
decisions = [
    ("Switch 透明款配色", "建议：红蓝经典配色 (3 款)", "确认数量及配色？"),
    ("婴童类市场进入", "A: 自主调研 (2 周) / B: 购买报告 (¥8000)", "选择方案？"),
    ("蜘蛛侠项目重启", "条件：市场需求明确 + 设计资源充足", "是否保留重启可能？"),
    ("助理资源优化", "许瑶可承担更多项目协调工作", "确认职责调整？"),
]
for title, proposal, decision in decisions:
    content.append(Paragraph(f"• {title}", h2_style))
    content.append(Paragraph(f"  建议方案：{proposal}", normal_style))
    content.append(Paragraph(f"  需决策：{decision}", normal_style))
    content.append(Spacer(1, 0.2*cm))
content.append(Spacer(1, 0.5*cm))

# ============ 总结 ============
content.append(Paragraph("总结与建议", h1_style))
content.append(Paragraph("整体健康度：🟢 良好（蜘蛛侠暂停后风险降低）", h2_style))
content.append(Spacer(1, 0.2*cm))
content.append(Paragraph("三大优先事项：", h2_style))
priorities = [
    "1️⃣ Switch 配色确认（本周决策）",
    "2️⃣ 女生书包加速推进（下周评审）",
    "3️⃣ 婴童类市场调研启动（3 月中旬）"
]
for p in priorities:
    content.append(Paragraph(p, normal_style))
content.append(Spacer(1, 0.3*cm))
content.append(Paragraph("资源建议：", h2_style))
suggestions = [
    "✓ 蜘蛛侠暂停后，设计产能已缓解",
    "✓ 许瑶可更多参与项目协调，提升团队效率",
    "✓ 建议评估蜘蛛侠项目未来重启条件"
]
for s in suggestions:
    content.append(Paragraph(s, normal_style))
content.append(Spacer(1, 1*cm))

# ============ 页脚信息 ============
content.append(Paragraph("_______________________________________", footer_style))
content.append(Paragraph("报告结束 | 下次自动汇报：2026-03-08", footer_style))
content.append(Paragraph("报告生成：AI 助手 [YOUR_AI_NAME]", footer_style))
content.append(Spacer(1, 0.2*cm))
content.append(Paragraph("附录：详细项目数据见飞书多维表格", footer_style))
content.append(Paragraph("原始数据 Token: UPcwbHbUwah0d4s937ncGpL1nQe", footer_style))

# 构建 PDF
print("正在生成 PDF...")
doc.build(content)

if os.path.exists(doc_path):
    size = os.path.getsize(doc_path) / 1024
    print(f"✅ PDF 已成功生成：{doc_path}")
    print(f"📦 文件大小：{size:.1f} KB")
    print(f"📄 页数：{doc.page}")
else:
    print("❌ PDF 生成失败")
    exit(1)
