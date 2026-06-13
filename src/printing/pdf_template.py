# -*- coding: utf-8 -*-
"""
pdf_template.py
李玉贤名医工作室标准处方打印模板
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm

def generate_prescription_pdf(data, out_path, paper="C6"):
    # 页面尺寸
    if paper == "C6":
        width, height = 114 * mm, 162 * mm
    else:
        width, height = A5
    c = canvas.Canvas(out_path, pagesize=(width, height))
    c.setFont("Helvetica", 10)
    y = height - 20 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, "李玉贤名医工作室标准处方笺")
    y -= 10 * mm

    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y, f"煎药方式：{data.get('jian_method','')}")
    c.drawString(70 * mm, y, f"日期：{data.get('date','')}")
    y -= 6 * mm
    c.drawString(15 * mm, y, f"节气：{data.get('jieqi','')}")
    c.drawString(70 * mm, y, f"五运六气：{data.get('yunqi','')}")
    y -= 10 * mm

    # 患者信息
    c.drawString(15 * mm, y, f"姓名：{data.get('patient_name','')}    性别：{data.get('gender','')}   年龄：{data.get('age','')}")
    y -= 6 * mm
    c.drawString(15 * mm, y, f"电话：{data.get('phone','')}   地址：{data.get('address','')}")
    y -= 10 * mm

    # 诊断部分
    c.drawString(15 * mm, y, f"临床诊断：{data.get('diagnosis_clinic','')}")
    y -= 5 * mm
    c.drawString(15 * mm, y, f"证型：{data.get('zhengxing','')}   治法：{data.get('zhilaw','')}")
    y -= 5 * mm
    c.drawString(15 * mm, y, f"西医诊断：{data.get('diagnosis_western','')}")
    y -= 8 * mm
    c.drawString(15 * mm, y, f"主诉：{data.get('complaint','')}")
    y -= 8 * mm
    c.drawString(15 * mm, y, f"现病史：{data.get('history','')}")
    y -= 8 * mm
    past = data.get('past_history','')
    if past:
        c.drawString(15 * mm, y, f"既往史：{past}")
        y -= 8 * mm
    exams = data.get("examinations", [])
    if exams:
        c.drawString(15 * mm, y, "辅助检查：")
        y -= 5 * mm
        c.setFont("Helvetica", 7)
        for ex in exams:
            text = f"  {ex.get('type','')}（{ex.get('date','')}）：{ex.get('summary','')}"
            c.drawString(18 * mm, y, text)
            y -= 4 * mm
        c.setFont("Helvetica", 9)
        y -= 2 * mm
    c.drawString(15 * mm, y, f"症状舌脉：{data.get('zhenghou','')}")
    y -= 10 * mm

    # 药物表格
    herbs = data.get("herbs", [])
    for i, herb in enumerate(herbs):
        text = f"{herb.get('name',''):<6} {herb.get('dose','')}g"
        c.drawString(20 * mm, y, text)
        remark = herb.get("remark","")
        if remark:
            c.setFont("Helvetica", 7)
            c.drawString(65 * mm, y + 3 * mm, remark)
            c.setFont("Helvetica", 9)
        if (i + 1) % 3 == 0:
            y -= 6 * mm
    y -= 8 * mm

    # 用法与签名
    c.drawString(15 * mm, y, f"用法：{data.get('usage','')}")
    y -= 6 * mm
    c.drawString(15 * mm, y, f"剂数：{data.get('dose_count','')}    医师签名：{data.get('doctor','')}    日期：{data.get('sign_date','')}")

    c.showPage()
    c.save()
    return out_path
