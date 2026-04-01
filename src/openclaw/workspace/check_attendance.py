"""
3月份考勤深度核查脚本
对比 考勤表-1.xls（原始打卡）vs 考勤综合表202603.xlsx（综合记录）

规则：
  - 外出（签退=外出）→ 记全勤，不算缺勤
  - 缺勤：签到签退都无记录，且综合表无对应请假备注 → 异常
  - 迟到：签到>9:00，9:01起算迟到（分钟）
  - 早退：签退<18:00
  - 加班：签退>22:00
  - 每月3次15分钟内迟到机会，超过次数登记合计分钟数
  - 综合表备注里有请假/调休等，视同出勤，不算缺勤
"""

import re, calendar
from datetime import datetime, time
import pandas as pd
from openpyxl import load_workbook

SRC = '/home/user/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/t7688103_6354/msg/file/2026-04/2026年3月考勤表-1.xls'
COMP = '/home/user/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/t7688103_6354/msg/file/2026-04/考勤综合表202603.xlsx'

YEAR, MONTH = 2026, 3
WORK_START   = time(9, 0)
WORK_END     = time(18, 0)
OT_THRESHOLD = time(22, 0)

# ─────────────────────────────────────────────────────────────────────────────
# 1. 解析考勤表-1
# ─────────────────────────────────────────────────────────────────────────────
df_xls = pd.read_excel(SRC, engine='xlrd', header=None)

emp_rows = [i for i, row in df_xls.iterrows()
            if str(row.iloc[0]) == '编号' and str(row.iloc[1]) not in ('nan', '')]

print(f"考勤表-1: {len(emp_rows)} 名员工")

employees = []
for idx in emp_rows:
    r = df_xls.iloc[idx]
    emp_id   = str(r.iloc[1])
    emp_name = str(r.iloc[8])   # col8 = name
    dept     = str(r.iloc[13]) if str(r.iloc[13]) != 'nan' else ''

    date_row  = df_xls.iloc[idx + 1]  # col0='日期', col1=day1 ...
    sin_row   = df_xls.iloc[idx + 2]  # col0='签到1'
    sout_row  = df_xls.iloc[idx + 3]  # col0='签退1'
    status_row= df_xls.iloc[idx + 9] if idx+9 < len(df_xls) else None  # 状态

    # xlrd: col1=day1, col2=day2, ... col31=day31
    days  = [str(date_row.iloc[j]) for j in range(1, 32)]
    sin   = [str(sin_row.iloc[j]) for j in range(1, 32)]
    sout  = [str(sout_row.iloc[j]) for j in range(1, 32)]
    stat  = [str(status_row.iloc[j]) if status_row is not None else '#' for j in range(1, 32)] if status_row is not None else ['#']*31

    employees.append({
        'emp_id': emp_id, 'emp_name': emp_name, 'dept': dept,
        'days': days, 'sign_in': sin, 'sign_out': sout, 'status': stat
    })

# ─────────────────────────────────────────────────────────────────────────────
# 2. 工作日（排除周末）
# ─────────────────────────────────────────────────────────────────────────────
non_workdays = set()
for d in range(1, 32):
    if calendar.weekday(YEAR, MONTH, d) >= 5:
        non_workdays.add(d)
print(f"周末天数: {len(non_workdays)}, 工作日: {22}")

WEEKDAY_NAMES = ['一','二','三','四','五','六','日']

def parse_time(s):
    s = str(s).strip()
    if s in ('-','','nan','None'): return None
    m = re.match(r'(\d{1,2}):(\d{2}):(\d{2})', s)
    if m: return time(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None

def tdelta_min(t_later, t_earlier):
    if t_later is None or t_earlier is None: return 0
    from datetime import timedelta
    return int((datetime.combine(datetime.today(), t_later) - datetime.combine(datetime.today(), t_earlier)).total_seconds() / 60)

# ─────────────────────────────────────────────────────────────────────────────
# 3. 解析综合表备注，提取各类请假/调休/加班/漏打卡等
# ─────────────────────────────────────────────────────────────────────────────
df_comp = pd.read_excel(COMP, sheet_name='3', header=1)
df_comp = df_comp[df_comp['姓名'].notna() & (df_comp['姓名'] != '')]

def parse_remarks(remark_str):
    """从综合表备注提取：年假/事假/病假/调休/加班/漏打卡/产检假日期"""
    if pd.isna(remark_str) or str(remark_str) == '':
        return {'leave': [], 'ot': [], 'miss_punch': [], 'note': ''}
    
    s = str(remark_str)
    leave = re.findall(r'(\d+)号((?:上午|下午|晚上)?(?:年假|事假|病假|丧假|婚假|陪产假|产假|产检假|调休)?)', s)
    leave = [(int(d), k) for d, k in leave]
    
    ot = re.findall(r'(\d+)号(加班)', s)
    ot = [int(d) for d, _ in ot]
    
    miss_in  = re.findall(r'(\d+)号上班忘打卡', s)
    miss_out = re.findall(r'(\d+)号下班忘打卡', s)
    miss_punch = [int(d) for d in miss_in + miss_out]
    
    # 年假/事假/病假/调休 - 记为已请假，不算缺勤
    leave_days = set(int(d) for d, _ in leave)
    
    return {'leave': leave_days, 'ot': set(ot), 'miss_punch': set(miss_punch), 'note': s}

comp_data = {}  # name -> {leave, ot, miss_punch, raw_note}
for _, row in df_comp.iterrows():
    name = str(row['姓名']).strip()
    remark = row['备注'] if '备注' in df_comp.columns else ''
    parsed = parse_remarks(remark)
    comp_data[name] = parsed

# ─────────────────────────────────────────────────────────────────────────────
# 4. 逐人分析
# ─────────────────────────────────────────────────────────────────────────────
report = []   # 最终问题列表

for emp in employees:
    name = emp['emp_name']
    comp = comp_data.get(name, {'leave': set(), 'ot': set(), 'miss_punch': set(), 'note': ''})

    late_days_detail = []    # [(day, min), ...]
    early_days_detail = []   # [(day, min), ...]
    ot_days_detail = []      # [(day, min), ...]
    absent_days = []         # [day, ...] - 真正的缺勤（无打卡且无请假）
    outside_days = []         # [day, ...] - 外出（全勤）
    miss_punch_days = []      # [day, ...] - 漏打卡

    for day_idx in range(31):
        day_num = day_idx + 1
        if day_num in non_workdays: continue

        si_val = emp['sign_in'][day_idx]
        so_val = emp['sign_out'][day_idx]
        si_t = parse_time(si_val)
        so_t = parse_time(so_val)

        # 外出判断
        if '外出' in so_val:
            outside_days.append(day_num)
            continue  # 不算缺勤

        # 漏打卡
        if day_num in comp['miss_punch']:
            miss_punch_days.append(day_num)
            continue

        # 缺勤（无签到也无签退）
        if si_t is None and so_t is None:
            # 检查是否有请假
            if day_num not in comp['leave']:
                absent_days.append(day_num)
            continue

        # 迟到
        if si_t is not None and si_t > WORK_START:
            late_min = tdelta_min(si_t, WORK_START)
            late_days_detail.append((day_num, late_min))

        # 早退
        if so_t is not None and so_t < WORK_END:
            early_min = tdelta_min(WORK_END, so_t)
            early_days_detail.append((day_num, early_min))

        # 加班
        if so_t is not None and so_t > OT_THRESHOLD:
            ot_min = tdelta_min(so_t, OT_THRESHOLD)
            ot_days_detail.append((day_num, ot_min))

    # ── 计算合计迟到分钟（3次15分钟内免费）─────────────────────────────
    # 规则：每人每月3次迟到机会，每次15分钟内不扣；超过3次或单次>15分钟，合计分钟数
    # 对所有迟到记录，先给每人3次免费（总15分钟），扣除后剩余为应扣分钟数
    # 若单次迟到>15分钟，超出部分全计（即使只有1次）
    free_min = 45   # 3次 × 15分钟
    total_late_min = sum(m for _, m in late_days_detail)
    late_count = len(late_days_detail)
    
    # 计算应扣分钟数
    if late_count == 0:
        deduct_late_min = 0
    elif late_count <= 3:
        # 不超过3次：只有超过15分钟的部分计入
        excess_min = sum(max(0, m - 15) for _, m in late_days_detail)
        deduct_late_min = excess_min
    else:
        # 超过3次：前3次中超过15分钟的+后N次的全部分钟数
        sorted_late = sorted(late_days_detail, key=lambda x: x[0])  # 按日期排序
        first3 = sorted_late[:3]
        rest = sorted_late[3:]
        excess_first3 = sum(max(0, m - 15) for _, m in first3)
        deduct_late_min = excess_first3 + sum(m for _, m in rest)

    # 综合表记录的迟到分钟
    comp_late_min = None
    if name in comp_data and not pd.isna(df_comp[df_comp['姓名']==name]['迟到（分）'].values[0] if len(df_comp[df_comp['姓名']==name]) > 0 else None):
        try:
            val = df_comp[df_comp['姓名']==name]['迟到（分）'].values[0]
            comp_late_min = float(val) if not pd.isna(val) else None
        except:
            comp_late_min = None

    # 综合表备注
    comp_note = comp['note']

    report.append({
        'emp_id': emp['emp_id'],
        'emp_name': name,
        'dept': emp['dept'],
        'late_days': late_days_detail,
        'late_count': late_count,
        'total_late_min': total_late_min,
        'deduct_late_min': deduct_late_min,
        'comp_late_min': comp_late_min,
        'early_days': early_days_detail,
        'ot_days': ot_days_detail,
        'absent_days': absent_days,
        'outside_days': outside_days,
        'miss_punch_days': miss_punch_days,
        'comp_note': comp_note,
    })

# ─────────────────────────────────────────────────────────────────────────────
# 5. 打印核查报告
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*80)
print("【一】有迟到记录的员工（3次15分钟内免费，超出计入）")
print("="*80)
late_emps = [r for r in report if r['late_count'] > 0]
late_emps.sort(key=lambda x: x['deduct_late_min'], reverse=True)
for r in late_emps:
    print(f"\n  {r['emp_name']}（{r['dept']}）")
    late_strs = [f'{d}号迟到{m}分钟' for d, m in r['late_days']]
    print(f"    迟到明细: {', '.join(late_strs)}")
    print(f"    迟到次数: {r['late_count']}次  总迟到: {r['total_late_min']}分钟  应扣: {r['deduct_late_min']}分钟")
    if r['comp_late_min'] is not None:
        diff = abs(r['comp_late_min'] - r['deduct_late_min'])
        status = '✓ 吻合' if r['comp_late_min'] == r['deduct_late_min'] else f'⚠ 差{diff}分钟'
        print(f"    ✅ 综合表记录: {r['comp_late_min']}分钟  {status}")

print("\n" + "="*80)
print("【二】有外出记录的员工（外出=全勤）")
print("="*80)
outside_emps = [r for r in report if r['outside_days']]
for r in outside_emps:
    print(f"  {r['emp_name']}: 外出 {r['outside_days']} → 记全勤")

print("\n" + "="*80)
print("【三】有早退记录的员工")
print("="*80)
early_emps = [r for r in report if r['early_days']]
for r in early_emps:
    early_strs = [f'{d}号{m}分钟' for d, m in r['early_days']]
    print(f"  {r['emp_name']}: 早退 {early_strs}")

print("\n" + "="*80)
print("【四】有加班记录的员工（签退>22:00）")
print("="*80)
ot_emps = [r for r in report if r['ot_days']]
for r in ot_emps:
    ot_strs = [f'{d}号{m}分钟' for d, m in r['ot_days']]
    print(f"  {r['emp_name']}: 加班 {ot_strs}")

print("\n" + "="*80)
print("【五】缺勤核查（无打卡且无请假/调休备注）")
print("="*80)
absent_emps = [r for r in report if r['absent_days']]
if absent_emps:
    for r in absent_emps:
        print(f"  ⚠ {r['emp_name']}（{r['dept']}）: 缺勤 {r['absent_days']}")
        if r['comp_note']:
            print(f"      综合表备注: {r['comp_note']}")
        else:
            print(f"      综合表备注: 无 → ❌ 缺勤无说明！")
else:
    print("  ✅ 所有缺勤均有对应请假/调休/加班记录")

print("\n" + "="*80)
print("【六】漏打卡核查")
print("="*80)
miss_emps = [r for r in report if r['miss_punch_days']]
for r in miss_emps:
    print(f"  {r['emp_name']}: 漏打卡 {r['miss_punch_days']} | 综合表备注: {r['comp_note']}")
