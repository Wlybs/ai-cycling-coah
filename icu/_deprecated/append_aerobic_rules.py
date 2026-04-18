import io
content = """
## 2026-04-13: 教练传授有氧自律法则 (Self-Regulation for Aerobic Rides)
运动员询问日常如何自主选择有氧时长与功率的对应关系。教练给出了针对快肌选手的“时长-功率滑动法则”：
1. 时长与功率呈严格反比：
   - 极长(>3.5h): 必须锁定 FatMax (165-185W)，孤立慢肌。
   - 中等(2-3h): 甜点二区 (185-205W)，性价比最高。
   - 偏短(1-1.5h): 强压二区/Tempo (210-230W)，抬高有氧下限。
2. 动态体感校准：利用“心率脱钩(Decoupling >5%)”和“说话测试(Conversation Test)”作为实时的功率熔断器。坚决抵制大容量+中高强度的“灰色地带(Grey Zone)”黑洞。
"""
with io.open('coach_memory/coach_log.md', 'a', encoding='utf-8') as f:
    f.write(content)
