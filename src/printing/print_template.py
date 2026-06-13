# -*- coding: utf-8 -*-
# src/print_template.py
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

def render_prescription_pdf(data: dict, pdf_path: str):
    """
    data字段：
      patient_name, gender, age, visit_date, department, doctor
      complaint, tongue_pulse, zhenghou, herbs:[{name,dose,unit,memo}]
      usage, advice
    """
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm
    )
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph("<para align=center><b><font size=16>中医处方笺</font></b></para>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 6))

    # 基本信息
    base_data = [
        [f"姓名：{data.get('patient_name','')}", f"性别：{data.get('gender','')}", f"年龄：{data.get('age','')}"],
        [f"就诊日期：{data.get('visit_date','')}", f"科室：{data.get('department','')}", f"医生：{data.get('doctor','')}"],
    ]
    t_base = Table(base_data, colWidths=[70*mm, 40*mm, 40*mm])
    t_base.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), 'SimSun', 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_base)
    story.append(Spacer(1, 6))

    # 诊疗信息
    def p(label, text):
        return Paragraph(f"<b>{label}</b> {text}", styles['BodyText'])

    story.append(p("主诉：", data.get("complaint","")))
    story.append(Spacer(1, 2))
    story.append(p("现病史：", data.get("history","")))
    story.append(Spacer(1, 2))
    past = data.get("past_history","")
    if past:
        story.append(p("既往史：", past))
        story.append(Spacer(1, 2))
    exams = data.get("examinations", [])
    if exams:
        story.append(p("辅助检查：", ""))
        for ex in exams:
            story.append(Paragraph(f"  {ex.get('type','')}（{ex.get('date','')}）：{ex.get('summary','')}", styles['BodyText']))
        story.append(Spacer(1, 2))
    story.append(p("舌脉：", data.get("tongue_pulse","")))
    story.append(Spacer(1, 2))
    story.append(p("证候：", data.get("zhenghou","")))
    story.append(Spacer(1, 6))

    # 草药表
    herbs = data.get("herbs", [])
    rows = [["药名", "剂量", "单位", "备注"]]
    for h in herbs:
        rows.append([
            h.get("name",""),
            h.get("dose",""),
            h.get("unit","g"),
            h.get("memo",""),
        ])
    t = Table(rows, colWidths=[70*mm, 25*mm, 20*mm, 55*mm])
    t.setStyle(TableStyle([
        ('FONT', (0,0), (-1,0), 'SimSun', 10),
        ('FONT', (0,1), (-1,-1), 'SimSun', 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.Color(0.98,0.98,0.98)]),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    # 用法/医嘱
    story.append(p("用法：", data.get("usage","")))
    story.append(Spacer(1, 2))
    story.append(p("医嘱：", data.get("advice","")))
    story.append(Spacer(1, 10))

    # 签名区
    sign = Paragraph("<para align=right>医师签名：______________</para>", styles['BodyText'])
    story.append(sign)

    doc.build(story)
