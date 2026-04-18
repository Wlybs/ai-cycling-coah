import io
content = """
## 2026-04-13: 教练明确LSD的时间与功率锚点
运动员询问针对其个人能力(FTP 300W)的LSD确切定义。教练界定：对于快肌主导型，LSD功率必须被严格压制在FatMax区间(165-195W, 55-65% FTP)，坚决不可越过200W的“垃圾发力点”；而LSD的时长门槛(Minimum Effective Dose)为3.5小时，上限为4.5小时。低于3小时只能算普通Endurance，无法触及深层脂肪代谢与慢肌重塑。
"""
with io.open('coach_memory/coach_log.md', 'a', encoding='utf-8') as f:
    f.write(content)
