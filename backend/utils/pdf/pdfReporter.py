# -*- coding: utf-8 -*-
import platform
from io import BytesIO
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from utils.datetime_utils import utc_now
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether, \
    Flowable
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from PIL import Image as PILImage
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import matplotlib

matplotlib.use('Agg')


class PageCountCanvas(canvas.Canvas):
    def __init__(self, company_name, time_zone, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.company_name = company_name
        try:
            self.time_zone = ZoneInfo(time_zone or "Asia/Shanghai")
        except ZoneInfoNotFoundError:
            self.time_zone = ZoneInfo("Asia/Shanghai")
        self.inch = inch * 0.75

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        company_name = self.company_name
        self.setFont('SimSun', 6)
        self.setFillColor(colors.ReportLabFidRed)
        self.rect(self.inch, self.inch - 15, 15, 15, fill=1, stroke=0)
        self.setFillColor(colors.black)
        self.setFillAlpha(0.8)
        self.rect(self.inch + 15, self.inch - 15, 10, 15, fill=1, stroke=0)
        self.setFillAlpha(0.6)
        self.rect(self.inch + 25, self.inch - 15, 5, 15, fill=1, stroke=0)
        # self.setFillColor(colors.lightgrey)
        self.setFillAlpha(0.2)
        self.rect(self.inch + 30, self.inch - 15, A4[0] - 2 * self.inch - 30, 15, fill=1, stroke=0)
        self.setFillColor(colors.black)

        displayed_now = utc_now().astimezone(self.time_zone)
        self.drawString(self.inch + 35, self.inch - 10, f"{displayed_now.strftime('%Y年%m月%d日')}")
        self.drawCentredString(A4[0] / 2.0, self.inch - 10,
                               f"{company_name}版权所有 ©2019-{displayed_now.strftime('%Y')} ")
        self.drawRightString(A4[0] - self.inch - 5, self.inch - 10, f"第 {self._pageNumber} 页 共 {page_count} 页")


class PDFReportGenerator:
    def __init__(self, company_name: str, logo_path: str | None, title: str, sub_title: str | None = None,
                 app: str = "ICRDB", time_zone: str | None = None):
        self._register_font()

        self.images = []
        self.sub_title = sub_title
        self.company_name = company_name
        self.logo_path = logo_path
        self.title = title
        self.app = app
        self.time_zone = time_zone
        self.elements = []
        self.title_index = 1
        self.styles = getSampleStyleSheet()
        self.styles.add(
            ParagraphStyle(name='Chinese', fontName='SimSun', fontSize=6, alignment=1, leading=12, spaceAfter=0))
        if self.logo_path:
            self._validate_logo_path()
        self._register_font()
        self.logo_rate = self._get_logo_rate() if self.logo_path else None
        self.inch = inch * 0.75
        self.inner_width = A4[0] - inch
        # 设置ECharts默认配色
        self.echarts_colors = ['#5470C6', '#91CC75', '#FAC858', '#EE6666', '#73C0DE', '#3BA272', '#FC8452', '#9A60B4',
                               '#EA7CCC']

    @staticmethod
    def _register_font():
        if platform.system() == 'Windows':
            font_path = 'C:/Windows/Fonts/msyh.ttc'
        elif platform.system() == 'Linux':
            font_path = '/usr/share/fonts/MSYH.TTC'
        else:
            font_path = None
        if font_path:
            pdfmetrics.registerFont(TTFont('SimSun', font_path))
            return font_path
            # plt.rc('font', family=font_prop.get_name())
        else:
            raise RuntimeError("Unsupported operating system or font path not found")

    @staticmethod
    def _register_plot_font():
        if platform.system() == 'Windows':
            font_path = 'C:/Windows/Fonts/msyh.ttc'
        elif platform.system() == 'Linux':
            font_path = '/usr/share/fonts/MSYH.TTC'
        else:
            font_path = None
        # Load the font if the path is valid
        if font_path and os.path.exists(font_path):
            prop = fm.FontProperties(fname=font_path)
        else:
            prop = fm.FontProperties()
        return prop

    def _validate_logo_path(self):
        if not os.path.exists(self.logo_path):
            raise FileNotFoundError(f"Logo file not found at path: {self.logo_path}")

    def _get_logo_rate(self):
        with PILImage.open(self.logo_path) as img:
            width, height = img.size
        # 设定一个最大宽度或高度
        return round(height / width, 1)

    def add_image_in_pdf(self):
        self.elements.append(self.images)
        self.images = []

    def create_cover_page(self):
        cover_style = ParagraphStyle(name='CoverTitle', fontName='SimSun', fontSize=28, alignment=1, spaceAfter=20)
        sub_title_style = ParagraphStyle(name='CoverTitle', fontName='SimSun', fontSize=10, alignment=1, spaceAfter=0)
        company_style = ParagraphStyle(name='CompanyName', fontName='SimSun', fontSize=12, alignment=1, spaceAfter=20)

        # 添加ICRDM标题
        self.elements.append(Spacer(1, 1.8 * inch))
        self.elements.append(Paragraph(self.title, cover_style))
        if self.sub_title:
            self.elements.append(Spacer(1, 5))
            self.elements.append(Paragraph(self.sub_title, sub_title_style))
        self.elements.append(Spacer(1, 1.8 * inch))

        # 添加公司Logo
        if self.logo_path:
            logo = Image(self.logo_path, width=350, height=int(350 * self.logo_rate))
            logo.hAlign = 'CENTER'
            self.elements.append(logo)
            self.elements.append(Spacer(1, 1.8 * inch))

        # 添加公司名称
        self.elements.append(Paragraph(self.company_name, company_style))
        self.elements.append(Paragraph(self.app, company_style))
        self.elements.append(PageBreak())

    def header(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('SimSun', 8)
        canvas.drawString(self.inch, A4[1] - self.inch + 2, "内参")  # 页眉距离顶部留有20的空白
        canvas.drawCentredString(A4[0] / 2.0, A4[1] - self.inch + 2, self.title)
        if self.logo_path:
            logo = Image(self.logo_path, 120, int(120 * self.logo_rate))
            logo.drawOn(canvas, A4[0] - 122 - self.inch, A4[1] - self.inch + 2)
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1)
        canvas.line(self.inch - 1, A4[1] - self.inch, A4[0] - self.inch - 1, A4[1] - self.inch)
        canvas.restoreState()

    def footer(self, *args, **kwargs):
        return PageCountCanvas(self.company_name, self.time_zone, *args, **kwargs)

    def add_table(self, data, title, col_width_ratios=None, hint=None, space=10):
        if len(data) <= 1:
            return
        title_style = ParagraphStyle(name='TableTile', fontName='SimSun', fontSize=10, alignment=1)
        # 增加标题索引
        indexed_title = f"{self.title_index}. {title}"
        if self.title_index == 1:
            self.elements.append(Spacer(A4[0], 20))  # 第一个标题增加间隙
        self.elements.append(Paragraph(indexed_title, title_style))
        self.elements.append(Spacer(1, 2))  # 标题和表格之间的间距

        if hint:
            hint_style = ParagraphStyle(name='Hint', fontName='SimSun', fontSize=6, alignment=0, leading=8)
            if isinstance(hint, list):
                hint_text = "<br/>".join([f"注：{h}" for h in hint])
            else:
                hint_text = f"注：{hint}"
            self.elements.append(Paragraph(hint_text, hint_style))
        total_width = A4[0] - 2 * self.inch  # 总宽度减去左右边距
        # 计算每列的宽度
        if col_width_ratios:
            all_ratio = sum(col_width_ratios)
            col_widths = [int(total_width * (ratio / all_ratio)) for ratio in col_width_ratios]
        else:
            col_widths = [total_width / len(data[0])] * len(data[0])
        # 使用Paragraph包装单元格内容
        cell_style = ParagraphStyle(name='CellStyle', fontName='SimSun', fontSize=6, alignment=1, leading=8,
                                    spaceAfter=0)
        table_data = [[Paragraph(str(cell), cell_style) for cell in row] for row in data]

        # 设置表格样式
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4CAF50")),  # 表头背景色
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # 表头文字颜色
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F2F2F2")),  # 表格背景色
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#D3D3D3")),  # 表格网格线颜色
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 垂直居中
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 水平居中
            ('ROWHEIGHT', (0, 0), (-1, 0), 40),  # 固定表头行高
            ('ROWHEIGHT', (0, 1), (-1, -1), 10),  # 固定数据行高
        ])

        table = Table(table_data, colWidths=col_widths)
        table.setStyle(table_style)
        self.elements.append(table)
        self.elements.append(Spacer(1, space))  # 表格和下一个标题之间的间距
        self.title_index += 1

    def create_main_title_page(self):
        main_title_style = ParagraphStyle(name='MainTitle', fontName='SimSun', fontSize=18, alignment=1, spaceAfter=20)
        copyright_style = ParagraphStyle(name='Copyright', fontName='SimSun', fontSize=12, alignment=1, spaceAfter=20)

        # 添加主标题
        self.elements.append(Spacer(1, 2 * inch))
        self.elements.append(Paragraph(self.title, main_title_style))
        self.elements.append(Spacer(1, 2 * inch))

        # 添加版权声明
        self.elements.append(Paragraph(f"{self.company_name} 版权所有", copyright_style))
        self.elements.append(PageBreak())

    def generate_pdf(self):
        output_pdf = BytesIO()
        doc = SimpleDocTemplate(output_pdf, pagesize=A4, leftMargin=self.inch, rightMargin=self.inch,
                                topMargin=self.inch,
                                bottomMargin=self.inch)
        doc.build(self.elements, onFirstPage=self.header, onLaterPages=self.header, canvasmaker=self.footer)
        return output_pdf

    def add_images_to_table(self, img_buffers, sizes, max_images_per_row=3):
        num_images = len(img_buffers)
        images_per_row = max_images_per_row
        image_width = int(self.inner_width / images_per_row) - 20

        data = []
        row = []
        for i, (img_buffer, size) in enumerate(zip(img_buffers, sizes)):
            aspect_ratio = size[1] / size[0]
            chart = Image(img_buffer, width=image_width, height=int(image_width * aspect_ratio))
            row.append(chart)
            if (i + 1) % images_per_row == 0 or i == num_images - 1:
                data.append(row)
                row = []

        col_widths = [image_width] * images_per_row
        table = Table(data, colWidths=col_widths)

        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        self.elements.append(table)

    def draw_pie_chart(self, data, labels, title):
        font_prop = self._register_plot_font()
        # 过滤掉显示为“0.0%”的数据
        total = sum(data)
        filtered_data_labels = [
            (d, label) for d, label in zip(data, labels) if (d / total) * 100 > 0.05
        ]
        if not filtered_data_labels:
            return None, (0, 0)

        data, labels = zip(*filtered_data_labels)

        fig_size = (5, 3.5)
        fig, ax = plt.subplots(figsize=fig_size, layout='constrained')
        ax.pie(data, colors=self.echarts_colors[:len(data)], labels=labels, autopct='%1.1f%%', startangle=90,
               wedgeprops={"linewidth": 1, "edgecolor": "white"})
        ax.set_title(title, fontsize=12, fontproperties=font_prop)
        ax.axis('equal')

        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        img_buffer.seek(0)
        img = PILImage.open(img_buffer)
        return img_buffer, img.size

    def add_pie_charts(self, datas, titles, categories, max_images_per_row=2):
        img_buffers, sizes = [], []
        for data, title, category in zip(datas, titles, categories):
            img_buffer, size = self.draw_pie_chart(data, category, title)
            if img_buffer:
                img_buffers.append(img_buffer)
                sizes.append(size)

        self.add_images_to_table(img_buffers, sizes, max_images_per_row=max_images_per_row)

    def draw_bar_group_chart(self, categories, metrics, data, x_label, y_label, title, max_images_per_row):
        font_prop = self._register_plot_font()
        x = np.arange(len(categories))
        num_categories = len(categories)
        width = 0.2 / max_images_per_row

        fig_size = (10 / max_images_per_row, 6 / max_images_per_row)
        fig, ax = plt.subplots(figsize=fig_size, layout='constrained')
        index = range(num_categories)

        for i, metric in enumerate(metrics):
            bar_data = [data[j][i] for j in range(num_categories)]
            bars = ax.bar([p + width * i for p in index], bar_data, width, label=metric, color=self.echarts_colors[i])
            for bar, value in zip(bars, bar_data):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2, f'{value}', ha='center', va='center',
                        fontsize=6, fontproperties=font_prop)

        ax.set_title(title, fontsize=12, fontproperties=font_prop)
        ax.set_xticks(x + width * (len(metrics) - 1) / 2)
        ax.set_xticklabels(categories, fontproperties=font_prop)
        ax.set_xlabel(x_label, fontproperties=font_prop)
        ax.set_ylabel(y_label, fontproperties=font_prop)
        ax.legend(prop=font_prop)

        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        img_buffer.seek(0)
        img = PILImage.open(img_buffer)
        return img_buffer, img.size

    def add_bar_group_chart(self, categories, metrics, data, x_label, y_label, title, max_images_per_row=1):
        img_buffer, size = self.draw_bar_group_chart(categories, metrics, data, x_label, y_label, title,
                                                     max_images_per_row)
        self.add_images_to_table([img_buffer], [size], max_images_per_row=max_images_per_row)

    def draw_stacked_bar_chart(self, used_data, available_data, x_labels, y_label, title):
        font_prop = self._register_plot_font()
        fig_size = (5, 3)
        fig, ax = plt.subplots(figsize=fig_size)

        bars1 = ax.bar(x_labels, used_data, width=0.5, color=self.echarts_colors[2], label='已使用')
        bars2 = ax.bar(x_labels, available_data, width=0.5, bottom=used_data, color=self.echarts_colors[5],
                       label='可用')

        ax.set_title(title, fontsize=12, fontproperties=font_prop)
        ax.set_ylabel(y_label, fontproperties=font_prop)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.xticks(rotation=45, fontproperties=font_prop)
        ax.legend(prop=font_prop)

        for bar1, bar2 in zip(bars1, bars2):
            height = bar1.get_height() + bar2.get_height()
            ax.text(bar1.get_x() + bar1.get_width() / 2, height / 2,
                    f'{int(height)}', ha='center', va='center', fontsize=8, fontproperties=font_prop)

        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        img_buffer.seek(0)
        img = PILImage.open(img_buffer)
        return img_buffer, img.size

    def add_stacked_bar_charts(self, used_datas, available_datas, titles, x_labels, y_labels, max_images_per_row=2):
        img_buffers, sizes = [], []
        for used_data, available_data, title, x_label, y_label in zip(used_datas, available_datas, titles, x_labels,
                                                                      y_labels):
            img_buffer, size = self.draw_stacked_bar_chart(used_data, available_data, x_label, y_label, title)
            if img_buffer:
                img_buffers.append(img_buffer)
                sizes.append(size)
        self.add_images_to_table(img_buffers, sizes, max_images_per_row=max_images_per_row)

    def add_stacked_bar_in_batches(self, used_datas, available_datas, titles, x_labels, y_labels, max_images_per_row=2):
        n = len(used_datas)
        num_batches = (n + max_images_per_row - 1) // max_images_per_row

        for i in range(num_batches):
            start_idx = i * max_images_per_row
            end_idx = min((i + 1) * max_images_per_row, n)

            batch_used_datas = used_datas[start_idx:end_idx]
            batch_available_datas = available_datas[start_idx:end_idx]
            batch_titles = titles[start_idx:end_idx]
            batch_x_labels = x_labels[start_idx:end_idx]
            batch_y_labels = y_labels[start_idx:end_idx]

            self.add_stacked_bar_charts(batch_used_datas, batch_available_datas, batch_titles, batch_x_labels,
                                        batch_y_labels, max_images_per_row)

    # def draw_treemap(self, data, title):
    #     sizes = []
    #     labels = []
    #     def add_data(d):
    #         for key, value in d.items():
    #             sizes.append(value)
    #             labels.append(key)
    #
    #     add_data(data)
    #     fig_size = (10, 10)
    #     fig, ax = plt.subplots(figsize=fig_size)
    #
    #     squarify.plot(sizes=sizes, label=labels, color=self.echarts_colors * 10, ax=ax)
    #     ax.set_title(title, fontsize=14)
    #     ax.axis('off')
    #
    #     img_buffer = BytesIO()
    #     plt.savefig(img_buffer, format='png', bbox_inches='tight')
    #     plt.close(fig)
    #     img_buffer.seek(0)
    #     img = PILImage.open(img_buffer)
    #     return img_buffer, img.size
    #
    # def add_tree_map_chart(self, data, title):
    #     img_buffer, size = self.draw_treemap(data=data, title=title)
    #     self.add_images_to_table([img_buffer], [size], max_images_per_row=1)
