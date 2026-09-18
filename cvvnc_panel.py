#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CVNC/CVVNC 方案自动生成面板"""
import os
import wx
from wx.lib.scrolledpanel import ScrolledPanel

from cvvnc_params_panel import CvvncParamsPanel


class CvvncPanel(ScrolledPanel):
    """CVNC/CVVNC 方案自动生成面板。

    外部通过 self.cvvnc_panel 访问；MainFrame 需要读：
      - rule_path / json_folder / template_path
      - first_sound / sort_mode / ensure_all_audio / keep_isolated_vowel
      - trans_mode（自动 / 强制二段式）
      - max_cv / max_vc / alias_strategy
      - ncv_enabled / tmpl_sort / tmpl_align
      - params（参数面板返回的 dict）
    """

    def __init__(self, parent, on_browse_file, on_browse_folder, on_generate):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="CVNC/CVVNC/NCV 方案自动生成")
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 5)

        # ---- 标记模式 ----
        trans_sizer = wx.BoxSizer(wx.HORIZONTAL)
        trans_label = wx.StaticText(self, label="标记模式：")
        self.trans_choice = wx.Choice(self, choices=["自动", "强制二段式"])
        self.trans_choice.SetSelection(0)
        trans_tip = wx.StaticText(
            self,
            label="（自动：按 RULE 与 JSON 段数判定；强制二段式：忽略 RULE，全部按两段式处理）"
        )
        trans_sizer.Add(trans_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        trans_sizer.Add(self.trans_choice, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        trans_sizer.Add(trans_tip, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(trans_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- 规则文件 ----
        rule_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.rule_text = wx.TextCtrl(self, size=(400, -1))
        btn_rule = wx.Button(self, label="浏览...")
        btn_rule.Bind(wx.EVT_BUTTON, lambda e: on_browse_file(e, self.rule_text))
        rule_sizer.Add(wx.StaticText(self, label="规则文件："), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        rule_sizer.Add(self.rule_text, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        rule_sizer.Add(btn_rule, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(rule_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- 声库文件夹 ----
        json_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.json_text = wx.TextCtrl(self, size=(400, -1))
        btn_json = wx.Button(self, label="浏览...")
        btn_json.Bind(wx.EVT_BUTTON, lambda e: on_browse_folder(e, self.json_text))
        json_sizer.Add(wx.StaticText(self, label="声库文件夹："), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        json_sizer.Add(self.json_text, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        json_sizer.Add(btn_json, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(json_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- 开头音类型 ----
        first_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.first_choice = wx.Choice(self, choices=["辅音 (- b)", "整音 (- bi_)"])
        self.first_choice.SetSelection(0)
        first_sizer.Add(wx.StaticText(self, label="开头音类型："), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        first_sizer.Add(self.first_choice, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(first_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- 保留单独纯元音整音 ----
        isolated_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.isolated_check = wx.CheckBox(self, label="保留单独纯元音整音（非开头位置的无辅音整音别名）")
        self.isolated_check.SetValue(False)
        isolated_sizer.Add(self.isolated_check, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(isolated_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- 最大别名数 ----
        maxalias_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.maxcv_text = wx.TextCtrl(self, value="1", size=(60, -1))
        self.maxvc_text = wx.TextCtrl(self, value="1", size=(60, -1))
        maxalias_sizer.Add(wx.StaticText(self, label="最大CV别名数："), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        maxalias_sizer.Add(self.maxcv_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        maxalias_sizer.Add(wx.StaticText(self, label="最大VC别名数："), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 15)
        maxalias_sizer.Add(self.maxvc_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        maxalias_sizer.Add(wx.StaticText(self, label="（0 = 不限制）"), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(maxalias_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- 重复别名策略 ----
        strategy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.alias_strategy_choice = wx.Choice(
            self, choices=["替换已有同别名条目", "强制后备别名（#1, #2...）"]
        )
        self.alias_strategy_choice.SetSelection(0)
        strategy_sizer.Add(wx.StaticText(self, label="重复别名策略："), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        strategy_sizer.Add(self.alias_strategy_choice, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(strategy_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- oto 排序 ----
        sort_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sort_choice = wx.Choice(self, choices=["自然排序", "分类排序"])
        self.sort_choice.SetSelection(1)
        sort_sizer.Add(wx.StaticText(self, label="oto 排序（无模板时）："), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sort_sizer.Add(self.sort_choice, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(sort_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- 模板设置（StaticBox）----
        tmpl_box = wx.StaticBox(self, label="模板设置（可选，留空则走普通生成）")
        tmpl_box_sizer = wx.StaticBoxSizer(tmpl_box, wx.VERTICAL)

        # 模板路径（一直显示）
        tmpl_path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.template_text = wx.TextCtrl(self, size=(400, -1))
        btn_template = wx.Button(self, label="浏览...")
        btn_template.Bind(wx.EVT_BUTTON, lambda e: on_browse_file(e, self.template_text))
        tmpl_path_sizer.Add(wx.StaticText(self, label="模板 oto："), 0,
                            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        tmpl_path_sizer.Add(self.template_text, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        tmpl_path_sizer.Add(btn_template, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        tmpl_box_sizer.Add(tmpl_path_sizer, 0, wx.EXPAND | wx.ALL, 3)

        # 模板选项（仅当有模板路径时显示）
        self.template_settings_sizer = wx.BoxSizer(wx.VERTICAL)

        tmpl_sort_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.tmpl_sort_choice = wx.Choice(self, choices=["按模板顺序", "按发音分类排序"])
        self.tmpl_sort_choice.SetSelection(0)
        tmpl_sort_sizer.Add(wx.StaticText(self, label="模板排序："), 0,
                            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        tmpl_sort_sizer.Add(self.tmpl_sort_choice, 0,
                            wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        self.template_settings_sizer.Add(tmpl_sort_sizer, 0, wx.EXPAND | wx.ALL, 3)

        tmpl_align_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.tmpl_align_choice = wx.Choice(
            self, choices=["严格匹配（本音频产不出 → 记缺失）",
                           "自动模糊（本音频产不出 → 按公式强制补产）"]
        )
        self.tmpl_align_choice.SetSelection(0)
        tmpl_align_sizer.Add(wx.StaticText(self, label="模板对齐："), 0,
                             wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        tmpl_align_sizer.Add(self.tmpl_align_choice, 0,
                             wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        self.template_settings_sizer.Add(tmpl_align_sizer, 0, wx.EXPAND | wx.ALL, 3)

        tmpl_box_sizer.Add(self.template_settings_sizer, 0, wx.EXPAND | wx.ALL, 3)
        self.template_settings_sizer.Show(False)

        sizer.Add(tmpl_box_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # 绑定模板路径变化 → 动态显示
        self.template_text.Bind(wx.EVT_TEXT, self._on_template_changed)

        # ---- 确保所有音频至少一条 ----
        ensure_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ensure_all_check = wx.CheckBox(self, label="确保所有音频至少有一条 oto")
        self.ensure_all_check.SetValue(True)
        ensure_sizer.Add(self.ensure_all_check, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(ensure_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- NCV 模式开关 ----
        ncv_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ncv_check = wx.CheckBox(self, label="NCV 模式：上一音直接链接下一整音")
        self.ncv_check.SetValue(False)
        self.ncv_check.SetToolTip(
            "启用后，上一音节的韵尾/元音会直接链接到下一音节的整音（而非辅音）"
        )
        ncv_sizer.Add(self.ncv_check, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 3)
        sizer.Add(ncv_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- 参数面板（子 Notebook）----
        params_label = wx.StaticText(self, label="oto 模板参数：")
        sizer.Add(params_label, 0, wx.ALL | wx.LEFT, 5)
        self.params_panel = CvvncParamsPanel(self)
        sizer.Add(self.params_panel, 1, wx.EXPAND | wx.ALL, 5)

        # ---- 联动 ----
        self.first_choice.Bind(wx.EVT_CHOICE, self._on_first_sound_changed)
        self.trans_choice.Bind(wx.EVT_CHOICE, self._on_trans_mode_changed)
        self._update_first_consonant_group()

        # ---- 生成按钮 ----
        self.generate_btn = wx.Button(self, label="生成 oto")
        self.generate_btn.Bind(wx.EVT_BUTTON, on_generate)
        sizer.Add(self.generate_btn, 0, wx.ALL | wx.CENTER, 5)

        # ---- 结果 ----
        sizer.Add(wx.StaticText(self, label="结果："), 0, wx.ALL | wx.LEFT, 5)
        self.result_text = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 300)
        )
        sizer.Add(self.result_text, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)
        self.SetupScrolling(scroll_x=False, scroll_y=True)

    # ---------- 内部联动 ----------

    def _on_first_sound_changed(self, event):
        self._update_first_consonant_group()

    def _update_first_consonant_group(self):
        """选「整音」时，灰掉「开头辅音」参数组"""
        enabled = (self.first_choice.GetSelection() == 0)
        self.params_panel.set_enabled("开头辅音", enabled)

    def _on_trans_mode_changed(self, event):
        """标记模式改变（字内衔接参数固定为 A/B 两组，无需切换页）"""
        pass

    def _on_template_changed(self, event):
        """模板路径变化 → 动态显示/隐藏模板选项"""
        has_template = bool(self.template_text.GetValue().strip())
        self.template_settings_sizer.Show(has_template)
        self.Layout()
        self.SetupScrolling(scroll_x=False, scroll_y=True)
        event.Skip()

    def _get_trans_mode(self):
        """返回 'auto' / '2seg'"""
        idx = self.trans_choice.GetSelection()
        if idx == 1:
            return '2seg'
        return 'auto'

    # ---------- 对外接口 ----------

    def get_values(self):
        """返回面板上所有配置，供 MainFrame 调用。"""
        max_cv = int(self.maxcv_text.GetValue().strip() or "0")
        max_vc = int(self.maxvc_text.GetValue().strip() or "0")
        if max_cv < 0 or max_vc < 0:
            raise ValueError("最大别名数不能为负数")

        return {
            'rule_path': self.rule_text.GetValue().strip(),
            'json_folder': self.json_text.GetValue().strip(),
            'template_path': self.template_text.GetValue().strip(),
            'first_sound': 'consonant' if self.first_choice.GetSelection() == 0 else 'onset',
            'keep_isolated_vowel': self.isolated_check.GetValue(),
            'trans_mode': self._get_trans_mode(),
            'max_cv': max_cv,
            'max_vc': max_vc,
            'alias_strategy': 'replace' if self.alias_strategy_choice.GetSelection() == 1 else 'backup',
            'sort_mode': 'natural' if self.sort_choice.GetSelection() == 0 else 'category',
            'ensure_all_audio': self.ensure_all_check.GetValue(),
            'ncv_enabled': self.ncv_check.GetValue(),
            'tmpl_sort': 'template' if self.tmpl_sort_choice.GetSelection() == 0 else 'category',
            'tmpl_align': 'auto' if self.tmpl_align_choice.GetSelection() == 1 else 'strict',
            'params': self.params_panel.get_params(),
        }

    def get_result_ctrl(self):
        return self.result_text