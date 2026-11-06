# -*- coding: utf-8 -*-
"""
tkinter + SQLite3 会員管理システム 印刷プレビュー（拡大縮小対応）版
member_print_preview.py をベースに、仕様書_プレビュー拡大縮小機能.md に基づき、
印刷プレビュー画面へ以下2機能を追加したもの。
  ① イメージ（PDFページ）の拡大・縮小機能
  ② プレビューウインドウ自体の拡大・縮小（リサイズ）機能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font

import os
import shutil
import tempfile
import sqlite3
import datetime
import fitz  # PyMuPDF: PDFページをプレビュー画像として描画するために使用
from PIL import Image, ImageTk
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors, pagesizes
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics

#-------------------------------------------------------------------
# 広域変数の設定
#-------------------------------------------------------------------
#db_path = "C:/Users/hisashi/Documents/未来クライム/2026_Advanceコース/2026-09-02_No6/2026-09-02/member.db"
db_path = "./member.db"
DB_NAME = db_path

#DB利用可否の状態
is_closing = False

# -------------------------------
# DB初期化
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    conn.execute("PRAGMA foreign_keys=ON")

# GENDERテーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS GENDER(
        GENDER_ID INTEGER PRIMARY KEY,
        GENDER_LBL TEXT
    )""")

# MEMBERテーブル
    cur.execute("""
    CREATE TABLE IF NOT EXISTS MEMBER(
        ID INTEGER PRIMARY KEY,
        NAME TEXT NOT NULL,
        KANA TEXT NOT NULL,
        ZIPCODE TEXT,
        ADDRESS TEXT,
        PHONE TEXT,
        GENDER_ID INTEGER,
        BIRTHDAY TEXT,
        FOREIGN KEY(GENDER_ID) REFERENCES GENDER(GENDER_ID)
    )""")

# 性別マスタ初期データ
    cur.execute("SELECT COUNT(*) FROM GENDER")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO GENDER VALUES (?,?)", [(1,"男性"),(2,"女性"),(9,"その他")])

    conn.commit()
#    conn.close()

# -------------------------------
# DB接続
# -------------------------------
def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

# --------------------------------
# 次フィールドへフォーカス移動
# --------------------------------
def focus_next(event):
    event.widget.tk_focusNext().focus()
    return "break"

# --------------------------------
# コンボボックスの値を選択状態にする
# --------------------------------
def select_all_combobox(event):
    event.widget.selection_range(0, tk.END)

# --------------------------------
# IDフィールドへフォーカス移動
# --------------------------------
def focus_to_id(event):
    combo_id.focus_set()
    combo_id.selection_range(0, tk.END)
    return "break"

# --------------------------------
# IDフィールドからフォーカス移動
# --------------------------------
def id_enter_and_next(event):
    on_id_enter()
    focus_next(event)

# --------------------------------
# IDフィールド選択時にフォーカス移動
# --------------------------------
def id_selected_and_next(event):
    on_id_selected(event)
    focus_next(event)

# -------------------------------
# 既存ID取得
# -------------------------------
# MEMBERテーブル全レコードの登録済IDを取得
def load_ids():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT ID, NAME FROM MEMBER ORDER BY ID")
    rows = []
    for r in cur.fetchall():
        # 8桁右寄せ固定幅15桁
        rows.append(f"{int(r[0]):>15}  {r[1]}")
    return rows

# -------------------------------
# ID数値取得
# -------------------------------
def extract_id(text):
    if not text:
        return ""
    return text.strip().split()[0]

# -------------------------------
# ID状態監視
# -------------------------------
def check_id_state(event=None):
    # 選択したIDの行を取得
    selected_text = combo_id.get()

    # IDのみを取り出す
    id_part = extract_id(selected_text)

    id_list = [extract_id(x) for x in existing_ids]

    if id_part in id_list:
        # 既存ID
        btn_insert.config(state="disabled")
        btn_update.config(state="normal")
        btn_delete.config(state="normal")
    else:
        # 新規ID
        btn_insert.config(state="normal")
        btn_update.config(state="disabled")
        btn_delete.config(state="disabled")
        clear_form_fields()

# -------------------------------
# ID 入力時
# -------------------------------
def on_id_enter(event=None):
    global is_closing

    if is_closing:
        return

    value = extract_id(combo_id.get())

    # 数値でなければ何もしない
    if not value.isdigit():
        return

    id_val = int(value)

    conn = get_conn()
    cur = conn.cursor()

    # DBに存在するか確認
    cur.execute("SELECT COUNT(*) FROM MEMBER WHERE ID=?", (id_val,))
    count = cur.fetchone()[0]

    conn.close()

    if count == 0:
        # 存在しなければ何もしない
        return

    # 存在すればレコード読込
    load_record(id_val)

# -------------------------------
# ID 選択時
# -------------------------------
def on_id_selected(event=None):
    global conn, cur
    selected_text = combo_id.get()
    id_part = extract_id(selected_text)

    if not id_part.isdigit():
        return

    # 表示を右寄せ固定
    combo_id.set(f"{int(id_part):>15}")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM MEMBER WHERE ID=?", (id_part,))
    row = cur.fetchone()
    conn.close()

    if row:
        entry_name.delete(0, tk.END)
        entry_name.insert(0, row[1])

        entry_kana.delete(0, tk.END)
        entry_kana.insert(0, row[2])

        entry_zip.delete(0, tk.END)
        entry_zip.insert(0, row[3])

        entry_address.delete(0, tk.END)
        entry_address.insert(0, row[4])

        entry_phone.delete(0, tk.END)
        entry_phone.insert(0, row[5])

        entry_birthday.delete(0, tk.END)
        entry_birthday.insert(0, row[7])

        # ---- 性別反映 ----
        gender_id = str(row[6]) if row[6] else ""
        combo_gender.set(f"{int(gender_id):>2}" if gender_id else "")

        for g in gender_data:
            if str(g[0]) == gender_id:
                label_gender_name.config(text=g[1])
                break

# -------------------------------
# 性別選択時
# -------------------------------
def on_gender_selected(event=None):
    selected_text = combo_gender.get()

    # GENDER_ID抽出
    gender_id = extract_id(selected_text)

    # 性別コードが数値以下ならば何もしない
    if not gender_id.isdigit():
        return

    # combobox表示をIDのみに変更
    combo_gender.set(f"{int(gender_id):>2}")

    # GENDER名を取得して右側に表示
    for g in gender_data:
        if str(g[0]) == gender_id:
            label_gender_name.config(text=g[1])
            break

# --------------------------------
# 性別フィールド選択時にフォーカス移動
# --------------------------------
def gender_selected_and_next(event):
    on_gender_selected(event)
    focus_next(event)

#--------------------------------
# 性別入力時
#--------------------------------
def on_gender_typed(event=None):
    text = combo_gender.get().strip()

    # 数字以外は無視
    if not text.isdigit():
        label_gender_name.config(text="")
        return

    # 右寄せ表示（2桁固定）
    combo_gender.set(f"{int(text):>2}")

    # GENDER_IDと一致する名称を探す
    for g in gender_data:
        if str(g[0]) == text:
            label_gender_name.config(text=g[1])
            return

    # 一致しない場合は空表示
    label_gender_name.config(text="")

# -------------------------------
# レコード読込
# -------------------------------
def load_record(id_value):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM MEMBER WHERE ID=?", (id_value,))
    row = cur.fetchone()
    conn.close()
    if row:
        entry_name.delete(0, tk.END)
        entry_name.insert(0, row[1])
        entry_kana.delete(0, tk.END)
        entry_kana.insert(0, row[2])
        entry_zip.delete(0, tk.END)
        entry_zip.insert(0, row[3])
        entry_address.delete(0, tk.END)
        entry_address.insert(0, row[4])
        entry_phone.delete(0, tk.END)
        entry_phone.insert(0, row[5])
        entry_birthday.delete(0, tk.END)
        entry_birthday.insert(0, row[7])

        # ---- 性別処理 ----
        gender_id = str(row[6]) if row[6] else ""
        combo_gender.set(f"{int(gender_id):>2}" if gender_id else "")
        for g in gender_data:
            if str(g[0]) == gender_id:
                label_gender_name.config(text=g[1])
                break

#--------------------------------
# 性別テーブル読み込み
#--------------------------------
def load_genders():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT GENDER_ID, GENDER_LBL FROM GENDER ORDER BY GENDER_ID")
    rows = cur.fetchall()

    conn.close()
    return rows

# -------------------------------
# バリデーション
# -------------------------------
def validate():
    id_part = extract_id(combo_id.get())

    if not id_part.isdigit():
        messagebox.showerror("エラー","IDは数値で入力してください")
        return False
    if not entry_name.get():
        messagebox.showerror("エラー","氏名必須")
        return False
    if entry_birthday.get():
        try:
            datetime.datetime.strptime(entry_birthday.get(), "%Y-%m-%d")
        except:
            messagebox.showerror("エラー","日付形式YYYY-MM-DD")
            return False
    return True

# -------------------------------
# 登録
# -------------------------------
def insert_data():
    if not validate(): return

    conn = get_conn()

    conn.execute("""
    INSERT INTO MEMBER VALUES (?,?,?,?,?,?,?,?)
    """,(extract_id(combo_id.get()),
         entry_name.get(),
         entry_kana.get(),
         entry_zip.get(),
         entry_address.get(),
         entry_phone.get(),
         extract_id(combo_gender.get()),
         entry_birthday.get()))

    conn.commit()
    conn.close()

    refresh_all()

# -------------------------------
# 更新
# -------------------------------
def update_data():
    if not validate(): return
    current_id = extract_id(combo_id.get())
    conn = get_conn()

    conn.execute("""
    UPDATE MEMBER SET NAME=?,KANA=?,ZIPCODE=?,ADDRESS=?,
    PHONE=?,GENDER_ID=?,BIRTHDAY=? WHERE ID=?
    """,(entry_name.get(),
         entry_kana.get(),
         entry_zip.get(),
         entry_address.get(),
         entry_phone.get(),
         extract_id(combo_gender.get()),
         entry_birthday.get(),
         extract_id(combo_id.get())))

    conn.commit()
    conn.close()

    refresh_all(keep_id = current_id, clear_fields=True)

    # 再度選択して有効化
    combo_id.set(f"{int(current_id):>15}")

# -------------------------------
# 削除
# -------------------------------
def delete_data():
#    global conn
    id_part = extract_id(combo_id.get())

    if not extract_id(combo_id.get()).isdigit(): return

    if messagebox.askyesno("確認","削除しますか？"):
        conn = get_conn()
        conn.execute("DELETE FROM MEMBER WHERE ID=?",(extract_id(combo_id.get()),))

        conn.commit()
        conn.close()

        refresh_all()

    # まだMEMBERレコードが残っていれば先頭のIDを選択
    if existing_ids:
        combo_id.set(existing_ids[0])
        check_id_state()

# ===============================================================
# 印刷関連（プレビュー → プリンター印刷 / PDF保存 / 中止）
# ===============================================================

# 会員一覧の見出しと列幅（用紙の左右にはみ出さないよう明示的に指定する）
# 氏名・カナ・住所の幅を広げてあり、氏名・カナは折り返しをしない（住所のみ折り返す）
PRINT_HEADERS = ["ID","氏名","カナ","〒番号","住所","電話番号","性別","生年月日"]
PRINT_COL_WIDTHS = [14*mm, 36*mm, 36*mm, 20*mm, 86*mm, 28*mm, 12*mm, 22*mm]
PRINT_ADDRESS_COL = 4  # PRINT_HEADERSにおける「住所」列のインデックス

# -------------------------------
# 印刷対象データ取得
# -------------------------------
def fetch_member_data():
    conn = get_conn()
    cur = conn.cursor()

    sql = ("SELECT ID,NAME,KANA,ZIPCODE,ADDRESS,PHONE, GENDER_LBL, BIRTHDAY "
           "FROM MEMBER LEFT JOIN GENDER ON MEMBER.GENDER_ID = GENDER.GENDER_ID "
           "ORDER BY ID")
    cur.execute(sql)
    data = cur.fetchall()

    conn.close()
    return data

# -------------------------------
# PDFファイル生成（プレビュー後の「印刷」「保存」共通処理）
# -------------------------------
def generate_pdf(filepath, data):
    # 列数が多く住所など長い項目もあるため、横向き(landscape)のA4を使用し、
    # 各列の幅を明示的に指定することで用紙の左右からはみ出さないようにする。
    # 住所のみ列幅に収まるよう自動的に折り返して表示し、氏名・カナは折り返しをしない。
    page_size = pagesizes.landscape(pagesizes.A4)
    doc = SimpleDocTemplate(filepath, pagesize=page_size,
                             leftMargin=15*mm, rightMargin=10*mm,
                             topMargin=15*mm, bottomMargin=10*mm)

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
    title_style   = ParagraphStyle(name="Title",   fontName="HeiseiMin-W3", fontSize=12)
    address_style = ParagraphStyle(name="Address", fontName="HeiseiMin-W3", fontSize=9, leading=11)

    def to_cell(col_index, value):
        text = "" if value is None else str(value)
        if col_index == PRINT_ADDRESS_COL:
            return Paragraph(text, address_style)  # 住所のみ折り返しを許可する
        return text  # 氏名・カナ等は折り返しをしないプレーン文字列のまま表示する

    body_rows = [[to_cell(i, v) for i, v in enumerate(row)] for row in data]

    elements = [Paragraph("会員一覧", title_style), Spacer(1, 10)]
    table = Table([PRINT_HEADERS] + body_rows, colWidths=PRINT_COL_WIDTHS, repeatRows=1)
    table.setStyle([
        ("GRID",(0,0),(-1,-1),0.5,colors.black),
        ("FONTNAME",(0,0),(-1,-1),"HeiseiMin-W3"),
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ])
    elements.append(table)
    doc.build(elements)

# -------------------------------
# プリンターへ送信
# -------------------------------
def send_to_printer(filepath):
    try:
        # 既定のPDF閲覧アプリの「印刷」動作を呼び出し、既定プリンターへ送信する
        os.startfile(filepath, "print")
        return True
    except OSError as e:
        messagebox.showerror("印刷エラー", f"プリンターへの送信に失敗しました。\n{e}")
        return False

# -------------------------------
# 印刷ボタン押下時：プレビュー画面表示
# （拡大・縮小機能、ウインドウリサイズ対応を含む）
# -------------------------------
def show_print_preview():
    data = fetch_member_data()

    if not data:
        messagebox.showinfo("情報", "出力する会員データがありません")
        return

    # 実際にPDFを生成し、そのページをそのまま画像化して表示する。
    # こうすることでプレビューとPDF出力の見た目を完全に一致させる。
    temp_path = os.path.join(tempfile.gettempdir(), "member_list_preview.pdf")
    try:
        generate_pdf(temp_path, data)
    except Exception as e:
        messagebox.showerror("エラー", f"PDF生成に失敗しました。\n{e}")
        return

    try:
        pdf_doc = fitz.open(temp_path)
    except Exception as e:
        messagebox.showerror("エラー", f"PDFの読み込みに失敗しました。\n{e}")
        return

    total_pages = pdf_doc.page_count

    # ---- 拡大・縮小機能の状態 ----
    BASE_ZOOM = 1.0                       # 100%相当の基準倍率（PDFポイントサイズと等倍）
    ZOOM_MIN, ZOOM_MAX, ZOOM_STEP = 0.5, 3.0, 0.25
    state = {
        "page": 0,
        "photo": None,
        "zoom": BASE_ZOOM,   # 現在の表示倍率
        "fit_mode": False,   # 「幅に合わせる」モードのON/OFF
    }
    resize_state = {"after_id": None}     # ウインドウリサイズのデバウンス用

    # ---- ウインドウ構築（拡大・縮小対応のためサイズ変更可能にする） ----
    win = tk.Toplevel(root)
    win.title("印刷プレビュー")
    win.transient(root)
    win.grab_set()
    win.geometry("650x800")       # 初期サイズ
    win.minsize(420, 420)         # 操作ボタン等が隠れない最小サイズ
    win.resizable(True, True)

    # ---- ① ズームコントロール ----
    zoom_frame = tk.Frame(win)
    zoom_frame.pack(pady=(10, 0))

    btn_zoom_out = tk.Button(zoom_frame, text="－", width=4)
    zoom_label = tk.Label(zoom_frame, text="100%", width=6, anchor="center")
    btn_zoom_in = tk.Button(zoom_frame, text="＋", width=4)
    btn_zoom_reset = tk.Button(zoom_frame, text="等倍")
    btn_zoom_fit = tk.Button(zoom_frame, text="幅に合わせる")

    btn_zoom_out.pack(side="left", padx=3)
    zoom_label.pack(side="left", padx=5)
    btn_zoom_in.pack(side="left", padx=3)
    btn_zoom_reset.pack(side="left", padx=10)
    btn_zoom_fit.pack(side="left", padx=3)

    # ---- ページ送り ----
    nav_frame = tk.Frame(win)
    nav_frame.pack(pady=(5, 0))

    page_label = tk.Label(nav_frame, text="")
    btn_prev = tk.Button(nav_frame, text="◀ 前へ")
    btn_next = tk.Button(nav_frame, text="次へ ▶")

    # ---- ② プレビュー表示領域（縦横スクロール対応・ウインドウに追従） ----
    canvas_frame = tk.Frame(win, padx=10, pady=10)
    canvas_frame.pack(fill="both", expand=True)

    v_scroll = tk.Scrollbar(canvas_frame, orient="vertical")
    h_scroll = tk.Scrollbar(canvas_frame, orient="horizontal")
    canvas = tk.Canvas(canvas_frame, bg="#d9d9d9", highlightthickness=0,
                        yscrollcommand=v_scroll.set,
                        xscrollcommand=h_scroll.set)
    v_scroll.config(command=canvas.yview)
    h_scroll.config(command=canvas.xview)

    canvas.grid(row=0, column=0, sticky="nsew")
    v_scroll.grid(row=0, column=1, sticky="ns")
    h_scroll.grid(row=1, column=0, sticky="ew")

    canvas_frame.rowconfigure(0, weight=1)
    canvas_frame.columnconfigure(0, weight=1)

    def render_page():
        page_no = state["page"]
        page = pdf_doc[page_no]
        page_rect = page.rect  # PDFページの元サイズ（ポイント単位）

        # ---- フィットモード時は表示領域の幅から倍率を逆算する ----
        if state["fit_mode"]:
            viewport_w = canvas.winfo_width()
            if viewport_w > 1:
                state["zoom"] = max(ZOOM_MIN, min(ZOOM_MAX, viewport_w / page_rect.width))

        zoom = state["zoom"]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        photo = ImageTk.PhotoImage(img)
        state["photo"] = photo  # ガベージコレクトされないよう参照を保持

        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas.config(scrollregion=(0, 0, pix.width, pix.height))

        zoom_label.config(text=f"{round(zoom * 100)}%")
        page_label.config(text=f"{page_no + 1} / {total_pages} ページ")
        btn_prev.config(state="normal" if page_no > 0 else "disabled")
        btn_next.config(state="normal" if page_no < total_pages - 1 else "disabled")
        btn_zoom_out.config(state="normal" if zoom > ZOOM_MIN else "disabled")
        btn_zoom_in.config(state="normal" if zoom < ZOOM_MAX else "disabled")

    def apply_zoom(new_zoom):
        # 倍率変更の前後でスクロール位置（表示比率）を可能な範囲で維持する
        x_ratio = canvas.xview()[0]
        y_ratio = canvas.yview()[0]

        state["zoom"] = max(ZOOM_MIN, min(ZOOM_MAX, new_zoom))
        state["fit_mode"] = False
        render_page()

        canvas.xview_moveto(x_ratio)
        canvas.yview_moveto(y_ratio)

    def zoom_in():
        apply_zoom(state["zoom"] + ZOOM_STEP)

    def zoom_out():
        apply_zoom(state["zoom"] - ZOOM_STEP)

    def zoom_reset():
        apply_zoom(BASE_ZOOM)

    def zoom_fit():
        state["fit_mode"] = True
        render_page()

    btn_zoom_in.config(command=zoom_in)
    btn_zoom_out.config(command=zoom_out)
    btn_zoom_reset.config(command=zoom_reset)
    btn_zoom_fit.config(command=zoom_fit)

    def go_prev():
        # ページを送っても現在の倍率設定は保持する
        if state["page"] > 0:
            state["page"] -= 1
            render_page()

    def go_next():
        if state["page"] < total_pages - 1:
            state["page"] += 1
            render_page()

    btn_prev.config(command=go_prev)
    btn_next.config(command=go_next)

    if total_pages > 1:
        btn_prev.pack(side="left", padx=5)
        page_label.pack(side="left", padx=10)
        btn_next.pack(side="left", padx=5)

    # ---- ③ ウインドウリサイズへの追従（デバウンス処理付き） ----
    def cancel_pending_resize():
        if resize_state["after_id"] is not None:
            win.after_cancel(resize_state["after_id"])
            resize_state["after_id"] = None

    def on_window_resize(event):
        # ウインドウ本体のサイズ変更時のみ処理する（子ウィジェットのConfigureは無視）
        if event.widget is not win:
            return
        cancel_pending_resize()
        resize_state["after_id"] = win.after(150, render_page)

    win.bind("<Configure>", on_window_resize)

    # ---- 印刷 / 保存 / 中止 ボタン ----
    action_frame = tk.Frame(win, pady=10)
    action_frame.pack()

    def on_print_to_printer():
        cancel_pending_resize()
        pdf_doc.close()  # ファイルロック解除
        if send_to_printer(temp_path):
            messagebox.showinfo("完了", "プリンターへ送信しました")
            win.destroy()

    def on_save_pdf():
        filepath = filedialog.asksaveasfilename(
            parent=win,
            title="PDFファイルに保存",
            defaultextension=".pdf",
            initialfile="member_list.pdf",
            filetypes=[("PDF ファイル", "*.pdf")])
        if not filepath:
            return
        cancel_pending_resize()
        pdf_doc.close()  # ファイルロック解除
        try:
            shutil.copyfile(temp_path, filepath)
        except Exception as e:
            messagebox.showerror("エラー", f"PDF保存に失敗しました。\n{e}")
            return
        messagebox.showinfo("完了", f"PDFを保存しました\n{filepath}")
        win.destroy()

    def on_cancel():
        cancel_pending_resize()
        pdf_doc.close()
        win.destroy()

    tk.Button(action_frame, text="プリンターで印刷", width=16,
              command=on_print_to_printer).grid(row=0, column=0, padx=5)
    tk.Button(action_frame, text="PDFファイルに保存", width=16,
              command=on_save_pdf).grid(row=0, column=1, padx=5)
    tk.Button(action_frame, text="中止", width=16,
              command=on_cancel).grid(row=0, column=2, padx=5)

    win.protocol("WM_DELETE_WINDOW", on_cancel)

    render_page()

# -------------------------------
# フォームクリア
# -------------------------------
def clear_form_fields():
    for e in [entry_name, entry_kana, entry_zip, entry_address, entry_phone, entry_birthday]:
        e.delete(0,tk.END)
    combo_gender.set("")
    label_gender_name.config(text="")

# -------------------------------
# 全体更新
# -------------------------------
def refresh_all(keep_id=None, clear_fields=False):
    global existing_ids
    existing_ids = load_ids()
    combo_id["values"] = existing_ids

    if keep_id:
        combo_id.set(f"{int(keep_id):>15}")
        check_id_state()
    else:
        combo_id.set("")
        check_id_state()

    if clear_fields:
        clear_form_fields()

    combo_id.focus_set() # カーソルをIDに移動
    combo_id.selection_range(0, tk.END) #テキストを全選択

#--------------------------------
# ウインドウを閉じる時
#--------------------------------
def on_closing():
#    global conn,
    global  is_closing

    is_closing = True

    if messagebox.askokcancel("終了確認", "アプリケーションを終了しますか？"):
#        try:
#            conn.close()     # ← ここでDBクローズ
#        except:
#            pass
        root.destroy()   # ← ウインドウ破棄

# ===============================
# GUI構築
# ===============================
init_db()
existing_ids = load_ids()

root = tk.Tk()
root.title("会員管理システム（印刷プレビュー・拡大縮小対応版）")
root.geometry("700x420")
root.protocol("WM_DELETE_WINDOW", on_closing)

frame = tk.Frame(root,padx=20,pady=15)
frame.pack(fill="x")

# ---- 左揃え統一配置 ----
labels = ["ID","氏名","カナ","郵便番号","住所","電話","性別","生年月日(西暦)"]
for i,l in enumerate(labels):
    tk.Label(frame,text=l,         anchor="w").grid(row=i,column=0,sticky="w",pady=4)
#    tk.Label(frame,text=l,width=10,anchor="w").grid(row=i,column=0,sticky="w",pady=4)

# 等幅フォント作成
mono_font = font.Font(family="MS Gothic", size=10)
style = ttk.Style()

def adjust_id_dropdown_width():
    values = combo_id["values"]
    if not values:
        return
    list_font = font.nametofont("TkDefaultFont")   # リスト部分の既定フォント
    need = max(list_font.measure(v) for v in values) + 30  # 余白・スクロールバー分
    extra = max(0, need - combo_id.winfo_width())
    style.configure("WideList.TCombobox", postoffset=(0, 0, extra, 0))

combo_id = ttk.Combobox(
    frame,
    width=15,       # comboboxのサイズ(15桁)
    font=mono_font,
    justify="right", # 右寄せの指定
    style="WideList.TCombobox",            # 2026-11-04 IDの既存レコード表示幅を調整のため、追加
    postcommand=adjust_id_dropdown_width   # 同上
)
combo_id.grid(row=0,column=1,sticky="w")
combo_id["values"] = existing_ids
combo_id.bind("<KeyRelease>",check_id_state)
combo_id.bind("<FocusIn>", select_all_combobox)
combo_id.bind("<FocusOut>", on_id_enter)
combo_id.bind("<Return>", id_enter_and_next)
combo_id.bind("<Tab>", focus_next)
combo_id.bind("<<ComboboxSelected>>", lambda e: id_selected_and_next(e))

# 入力フィールド左揃え
entry_name = tk.Entry(frame,width=30); entry_name.grid(row=1,column=1,sticky="w")
entry_kana = tk.Entry(frame,width=30); entry_kana.grid(row=2,column=1,sticky="w")
entry_zip = tk.Entry(frame,width=15); entry_zip.grid(row=3,column=1,sticky="w")
entry_address = tk.Entry(frame,width=40); entry_address.grid(row=4,column=1,sticky="w")
entry_phone = tk.Entry(frame,width=25); entry_phone.grid(row=5,column=1,sticky="w")

# ---- 性別 Combobox ----
gender_data = load_genders()

# 表示用リスト作成（例: " 1  男性"）
gender_display = [f"{int(g[0]):>3}  {g[1]}" for g in gender_data]

def adjust_gender_dropdown_width():
    values = combo_gender["values"]
    if not values:
        return
    list_font = font.nametofont("TkDefaultFont")
    need = max(list_font.measure(v) for v in values) + 30  # 余白・スクロールバー分
    extra = max(0, need - combo_gender.winfo_width())
    style.configure("WideGender.TCombobox", postoffset=(0, 0, extra, 0))

gender_frame = tk.Frame(frame)
gender_frame.grid(row=6,column=1,sticky="w")

combo_gender = ttk.Combobox(gender_frame, width=3, justify="right",
                            style="WideGender.TCombobox",            # 性別のドロップダウンリストの表示幅自動調整
                            postcommand=adjust_gender_dropdown_width) # 同上

combo_gender.pack(side="left")
combo_gender["values"] = gender_display

# 右側に表示するラベル
label_gender_name = tk.Label(gender_frame, text="", anchor="w")
label_gender_name.pack(side="left", padx=5)

combo_gender.bind("<KeyRelease>", on_gender_typed)
combo_gender.bind("<Return>", focus_next)
combo_gender.bind("<Tab>", focus_next)
combo_gender.bind("<<ComboboxSelected>>", gender_selected_and_next)
combo_gender.bind("<FocusIn>", select_all_combobox)

# 生年月日用フレームを生成
birthday_frame = tk.Frame(frame)
birthday_frame.grid(row=7, column=1, sticky="w")

# 生年月日 + 右側フォーマット表示
entry_birthday = tk.Entry(birthday_frame, width=15)
entry_birthday.pack(side="left")
entry_birthday.bind("<Return>", focus_to_id)
entry_birthday.bind("<Tab>", focus_to_id)

# 生年月日入力フィールドの右側に(YYYY-MM-DD)と表示
label_birthday_fmt = tk.Label(birthday_frame, text="(YYYY-MM-DD)", anchor="w")
label_birthday_fmt.pack(side="left", padx=5)


# ---- ボタン 等幅横並び ----
btn_frame = tk.Frame(root,pady=15)
btn_frame.pack(fill="x")

btn_insert = tk.Button(btn_frame,text="登録",width=12,command=insert_data)
btn_update = tk.Button(btn_frame,text="更新",width=12,command=update_data)
btn_delete = tk.Button(btn_frame,text="削除",width=12,command=delete_data)
btn_print  = tk.Button(btn_frame,text="印刷",width=12,command=show_print_preview)
btn_exit   = tk.Button(btn_frame,text="終了",width=12,command=on_closing)

btn_insert.grid(row=0,column=0,padx=5)
btn_update.grid(row=0,column=1,padx=5)
btn_delete.grid(row=0,column=2,padx=5)
btn_print.grid(row=0,column=3,padx=5)
btn_exit.grid(row=0, column=4, padx=5)

# 各入力フィールドにフォーカス移動キーの動作を定義
for w in [entry_name, entry_kana, entry_zip, entry_address, entry_phone]:
    w.bind("<Return>", focus_next)
    w.bind("<Tab>", focus_next)

# MEMBERテーブル先頭レコードのIDを選択状態にする
#if existing_ids:
#    combo_id.set(existing_ids[0])
#    on_id_selected()

root.mainloop()
