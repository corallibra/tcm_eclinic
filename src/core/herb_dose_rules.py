# -*- coding: utf-8 -*-
"""
TCM 药材剂量安全范围验证规则

用途：防止处方中出现超常规或有毒药材用量（如麻黄、附子、乌头等）

数据来源：《中国药典》+ 临床经验数据库
可配置化，便于扩展新的药材规则。
"""


class TCM_DoseRule:
    """药材剂量安全规则库"""

    # 定义数据结构：{药材名： (最小 g, 最大 g, 备注)}
    DOSE_RULES = {
        "当归": (5.0, 30.0),           # 补血活血，常规 10-20g
        "川芎": (2.0, 15.0),          # 行气活血，注意用量过大可能兴奋中枢
        "白芍": (6.0, 30.0),
        "白术": (6.0, 30.0),
        "茯苓": (10.0, 60.0),          # 健脾利水，常用量偏大
        "陈皮": (5.0, 20.0),           # 理气化痰
        "甘草": (3.0, 15.0),           # 调和诸药，注意"十八反"禁忌

        # ⚠️ 有毒/慎用类（严格限制）
        "麻黄": (2.0, 9.0),            # 《中国药典》规定用量 3-10g（但临床谨慎用 ≤5g）
        "附子": (3.0, 15.0),           # 炮制后毒性降低，生附子禁用于处方
        "乌头": (3.0, 9.0),            # 同样剧毒，需特殊审批
        "细辛": (1.0, 6.0),            # "细辛不过钱"（约 3-4g）
        "半夏": (3.0, 12.0),           # 生半夏有毒，必须炮制

        # ⚠️ 补益类过量可能引起"上火"
        "人参": (5.0, 9.0),            # 《本草纲目》：人参补气，过用助火
        "黄芪": (10.0, 60.0),          # 常用量较大（如 30g）可治气虚血瘀
        "鹿茸": (1.0, 5.0),            # 大热之品，少量即可
    }

    @classmethod
    def is_valid_dose(cls, herb_name: str, dose: float) -> tuple[bool, str]:
        """验证剂量是否在安全范围内

        Args:
            herb_name: 药材标准名称（如"当归"）
            dose: 当前处方剂量（g）

        Returns:
            (是否通过，错误消息)
        """

        rule = cls.DOSE_RULES.get(herb_name)

        if not rule:
            return True, ""  # 未知药材不限制，但应在药材库中登记

        min_dose, max_dose = rule
        error_msg = f"药材{herb_name}剂量 {dose:.1f}g 超出标准范围 [{min_dose}-{max_dose}]g"

        return (min_dose <= dose <= max_dose), error_msg


# ============================================================================
# 示例验证
# ============================================================================
if __name__ == "__main__":
    # 合法剂量
    name, msg = TCM_DoseRule.is_valid_dose("当归", 15.0)
    print(f"当归 15g: {'✓' if name else '✗'} - {msg}")

    # 过量
    name, msg = TCM_DoseRule.is_valid_dose("麻黄", 12.0)
    print(f"麻黄 12g: {'✓' if name else '✗'} - {msg}")

    # 正常范围边缘值
    for herb in ["当归", "麻黄", "人参"]:
        max_d = TCM_DoseRule.DOSE_RULES[herb][1]
        min_d = TCM_DoseRule.DOSE_RULES[herb][0]
        print(f"{herb}: [{min_d}-{max_d}]g")
