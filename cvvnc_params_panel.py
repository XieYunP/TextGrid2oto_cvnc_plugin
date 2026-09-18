#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CVNC/CVVNC oto 模板参数面板"""
import wx
from wx.lib.scrolledpanel import ScrolledPanel


# ── 共用参数组 ──
COMMON_GROUPS = [
    ("开头辅音", [
        ("左边界向左偏移", "75", "ms（超出音频头取头）"),
        ("固定", "30", "%（左→右之间偏左）"),
        ("重叠", "30", "%（左→预之间偏左）"),
    ]),
    ("整音-无介母", [
        ("右边界", "65", "%（辅音起点→元音结束之间偏右）"),
        ("固定", "30", "%（预→右之间偏左）"),
        ("重叠", "30", "%（左→预之间偏左）"),
    ]),
    ("整音-有介母", [
        ("右边界", "15", "%（元音段前，即介母/主元音分界点）"),
        ("固定", "30", "%（预→右之间偏左）"),
        ("重叠", "30", "%（左→预之间偏左）"),
    ]),
    ("开头纯元音", [
        ("左边界向左偏移", "75", "ms（超出音频头取头）"),
        ("右边界", "65", "%（元音段后）"),
        ("固定", "15", "%（预→右之间偏左）"),
        ("重叠", "30", "%（左→预之间偏左）"),
    ]),
    ("非开头纯元音", [
        ("右边界", "65", "%（元音段后）"),
        ("预发声位置", "15", "%（元音起点→右边界之间偏右）"),
        ("固定", "15", "%（预→右之间偏左）"),
        ("重叠", "30", "%（左→预之间偏左）"),
    ]),
    ("coda R", [
        ("左边界", "75", "%（韵尾段或元音段起点→结束之间偏右 0=韵尾段或元音终点）"),
        ("右偏移", "150", "ms（预发声之后再往右，超出音频尾取尾）"),
        ("固定", "30", "%（预→右之间偏左）"),
        ("重叠位置", "50", "%（左→预之间偏右）"),
    ]),
    ("元音→辅音", [
        ("左边界", "65", "%（韵尾段或元音段后）"),
        ("固定", "30", "%（预→下一辅音中点之间偏左）"),
        ("重叠", "30", "%（左→预之间偏左）"),
    ]),
    ("元音→整音", [
        ("左边界", "65", "%（韵尾段或元音段后）"),
        ("右边界", "65", "%（下一元音段后）"),
        ("固定", "30", "%（预→右之间偏左）"),
        ("重叠", "30", "%（左→预之间偏左）"),
    ]),
]

# ── 字内衔接参数（2 组）──
TRANS_A_PARAMS = [
    ("分界点", "15", "%（元音段起点→结束之间偏右，=介母/主元音分界点）"),
    ("右边界", "65", "%（元音段起点→结束之间偏右；有独立韵尾段时改用韵尾起点）"),
    ("固定", "30", "%（预→右之间偏左）"),
    ("重叠", "100", "%（左→预之间偏右；100%=与预发声重合）"),
]

TRANS_B_PARAMS = [
    ("左边界", "65", "%（元音起点→韵尾起点之间偏右）"),
    ("假定韵尾起点", "75", "%（无独立韵尾段时，元音段起点→结束之间偏右）"),
    ("固定", "30", "%（预→韵尾结束之间偏左）"),
    ("重叠", "50", "%（左→预之间偏右）"),
]


def _make_param_page(parent, params, cols=3):
    """通用：把一组参数渲染到一个 Panel 里，返回 (panel, ctrl_list)"""
    page = wx.Panel(parent)
    page_sizer = wx.FlexGridSizer(rows=0, cols=cols, vgap=6, hgap=8)
    page_sizer.AddGrowableCol(1, 0)
    page_sizer.AddGrowableCol(2, 1)

    ctrl_list = []
    for display, default, unit in params:
        lbl = wx.StaticText(page, label=f"{display}：", size=(150, -1))
        ctrl = wx.TextCtrl(page, value=default, size=(70, -1))
        unit_lbl = wx.StaticText(page, label=unit)
        page_sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        page_sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        page_sizer.Add(unit_lbl, 1, wx.ALIGN_CENTER_VERTICAL)
        ctrl_list.append((display, ctrl))

    page.SetSizer(page_sizer)
    return page, ctrl_list


class CvvncParamsPanel(ScrolledPanel):
    """CVNC/CVVNC 参数面板。

    - 共用参数组
    - 字内衔接：两组参数（类型 A 介母→主元音 / 类型 B 主元音→韵尾）
    """

    def __init__(self, parent):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sub_nb = wx.Notebook(self)
        self.controls = {}

        # 1) 共用参数页
        for group_name, params in COMMON_GROUPS:
            page, ctrl_list = _make_param_page(sub_nb, params)
            sub_nb.AddPage(page, group_name)
            self.controls[group_name] = ctrl_list

        # 2) 字内衔接页：两组 StaticBox
        trans_page = wx.Panel(sub_nb)
        trans_sizer = wx.BoxSizer(wx.VERTICAL)

        # 2a) 介母→主元音
        box_a = wx.StaticBox(trans_page, label="字内衔接-介母→主元音")
        box_a_sizer = wx.StaticBoxSizer(box_a, wx.VERTICAL)
        page_a, ctrl_a = _make_param_page(trans_page, TRANS_A_PARAMS)
        box_a_sizer.Add(page_a, 0, wx.EXPAND | wx.ALL, 3)
        trans_sizer.Add(box_a_sizer, 0, wx.EXPAND | wx.ALL, 4)
        self.controls["字内衔接-介母→主元音"] = ctrl_a

        # 2b) 主元音→韵尾
        box_b = wx.StaticBox(trans_page, label="字内衔接-主元音→韵尾")
        box_b_sizer = wx.StaticBoxSizer(box_b, wx.VERTICAL)
        page_b, ctrl_b = _make_param_page(trans_page, TRANS_B_PARAMS)
        box_b_sizer.Add(page_b, 0, wx.EXPAND | wx.ALL, 3)
        trans_sizer.Add(box_b_sizer, 0, wx.EXPAND | wx.ALL, 4)
        self.controls["字内衔接-主元音→韵尾"] = ctrl_b

        trans_page.SetSizer(trans_sizer)
        sub_nb.AddPage(trans_page, "字内衔接")

        sizer.Add(sub_nb, 1, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(sizer)
        self.SetupScrolling(scroll_x=False, scroll_y=True)

    # ── 对外接口 ──

    def get_params(self):
        """返回全部参数（字内衔接 A/B 两组都返回）"""
        result = {}
        for group_name, ctrl_list in self.controls.items():
            for display, ctrl in ctrl_list:
                raw = ctrl.GetValue().strip()
                try:
                    val = float(raw) if raw else 0.0
                except ValueError:
                    raise ValueError(f"参数 {group_name}.{display} 的值 '{raw}' 不是数字")
                result[f"{group_name}.{display}"] = val
        return result

    def set_enabled(self, group_name, enabled):
        if group_name not in self.controls:
            return
        for _, ctrl in self.controls[group_name] or []:
            ctrl.Enable(enabled)