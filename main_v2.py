import os
import sys
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import numpy as np
import cv2
from PIL import Image, ImageTk

# TkinterDnDとCustomTkinterを統合するクラス
class DnDCustomTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class ImageVariationGenerator(DnDCustomTk):
    def __init__(self):
        super().__init__()
        
        # CTkインターフェイスの設定
        ctk.set_appearance_mode("dark")  # ダークモード
        ctk.set_default_color_theme("blue")  # カラーテーマ
        
        self.title("Color Variation Generator")
        self.geometry("900x700")
        self.minsize(900, 700)
        
        # フォント設定
        self.default_font = ("Yu Gothic UI", 10)
        self.header_font = ("Yu Gothic UI", 12, "bold")
        self.button_font = ("Yu Gothic UI", 10)
        
        # 変数の初期化
        self.input_image_path = ctk.StringVar()
        self.output_dir = ctk.StringVar()
        self.hue_variations = ctk.IntVar(value=10)
        self.saturation_variations = ctk.IntVar(value=3)
        self.r_scale = ctk.DoubleVar(value=1.0)  # 0.0～1.0で表示
        self.g_scale = ctk.DoubleVar(value=1.0)
        self.b_scale = ctk.DoubleVar(value=1.0)
        
        # RGB値変更時のコールバック設定
        self.r_scale.trace_add("write", self.on_rgb_change)
        self.g_scale.trace_add("write", self.on_rgb_change)
        self.b_scale.trace_add("write", self.on_rgb_change)
        
        self.preview_image = None
        self.original_image = None
        self.original_cv_image = None
        self.progress_var = ctk.DoubleVar(value=0)
        self.status_var = ctk.StringVar(value="待機中")
        
        # UIの構築
        self.create_widgets()
        
        # ドラッグ&ドロップの設定
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop)
    
    def create_widgets(self):
        # メインレイアウト（グリッドシステム）
        self.grid_columnconfigure(0, weight=3)  # プレビューエリア（大きめ）
        self.grid_columnconfigure(1, weight=1)  # コントロールエリア
        self.grid_rowconfigure(0, weight=1)
        
        # 左側のフレーム (画像プレビュー用)
        preview_frame = ctk.CTkFrame(self)
        preview_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)
        
        preview_label = ctk.CTkLabel(preview_frame, text="プレビュー", font=self.header_font)
        preview_label.grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        
        preview_container = ctk.CTkFrame(preview_frame)
        preview_container.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        preview_frame.grid_rowconfigure(1, weight=1)
        
        self.preview_label = ctk.CTkLabel(preview_container, text="", image=None)
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # ドロップゾーンのテキスト
        self.drop_text = ctk.CTkLabel(
            preview_container, 
            text="ここに画像をドラッグ＆ドロップしてください\nまたは「ファイルを選択」ボタンをクリックしてください",
            font=self.default_font
        )
        self.drop_text.place(relx=0.5, rely=0.5, anchor="center")
        
        # 右側のフレーム (コントロール用)
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        control_frame.grid_columnconfigure(0, weight=1)
        
        # 入力画像選択
        input_group = ctk.CTkFrame(control_frame)
        input_group.grid(row=0, column=0, padx=5, pady=(5, 10), sticky="ew")
        input_group.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(input_group, text="入力画像", font=self.header_font).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.path_entry = ctk.CTkEntry(input_group, textvariable=self.input_image_path)
        self.path_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        btn_browse = ctk.CTkButton(input_group, text="ファイルを選択", command=self.browse_file, font=self.button_font)
        btn_browse.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        # バリエーション設定
        variation_group = ctk.CTkFrame(control_frame)
        variation_group.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
        variation_group.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(variation_group, text="バリエーション設定", font=self.header_font).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(variation_group, text="色相バリエーション数:", font=self.default_font).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_hue = ctk.CTkEntry(variation_group, textvariable=self.hue_variations, width=80)
        entry_hue.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(variation_group, text="彩度バリエーション数:", font=self.default_font).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        entry_sat = ctk.CTkEntry(variation_group, textvariable=self.saturation_variations, width=80)
        entry_sat.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # RGB調整
        rgb_group = ctk.CTkFrame(control_frame)
        rgb_group.grid(row=2, column=0, padx=5, pady=10, sticky="ew")
        rgb_group.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(rgb_group, text="RGB強度調整", font=self.header_font).grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(rgb_group, text="R:", font=self.default_font, text_color="#FF5555").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkSlider(rgb_group, from_=0, to=2, variable=self.r_scale, number_of_steps=20).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.r_label = ctk.CTkLabel(rgb_group, text="1.0", font=self.default_font)
        self.r_label.grid(row=1, column=2, padx=5, pady=5, sticky="e")
        
        ctk.CTkLabel(rgb_group, text="G:", font=self.default_font, text_color="#55FF55").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkSlider(rgb_group, from_=0, to=2, variable=self.g_scale, number_of_steps=20).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.g_label = ctk.CTkLabel(rgb_group, text="1.0", font=self.default_font)
        self.g_label.grid(row=2, column=2, padx=5, pady=5, sticky="e")
        
        ctk.CTkLabel(rgb_group, text="B:", font=self.default_font, text_color="#5555FF").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkSlider(rgb_group, from_=0, to=2, variable=self.b_scale, number_of_steps=20).grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.b_label = ctk.CTkLabel(rgb_group, text="1.0", font=self.default_font)
        self.b_label.grid(row=3, column=2, padx=5, pady=5, sticky="e")
        
        # 出力先設定
        output_group = ctk.CTkFrame(control_frame)
        output_group.grid(row=3, column=0, padx=5, pady=10, sticky="ew")
        output_group.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(output_group, text="出力先フォルダ", font=self.header_font).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        self.output_entry = ctk.CTkEntry(output_group, textvariable=self.output_dir)
        self.output_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        btn_frame = ctk.CTkFrame(output_group, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        btn_output = ctk.CTkButton(btn_frame, text="フォルダを選択", command=self.browse_output_dir, font=self.button_font)
        btn_output.grid(row=0, column=0, padx=2, pady=0, sticky="ew")

        btn_open_folder = ctk.CTkButton(btn_frame, text="フォルダを開く", command=lambda: self.open_folder(self.output_dir.get()), font=self.button_font)
        btn_open_folder.grid(row=0, column=1, padx=2, pady=0, sticky="ew")
        
        # 実行ボタンとプログレスバー
        action_group = ctk.CTkFrame(control_frame)
        action_group.grid(row=4, column=0, padx=5, pady=(10, 5), sticky="ew")
        action_group.grid_columnconfigure(0, weight=1)
        
        self.btn_generate = ctk.CTkButton(
            action_group, 
            text="バリエーションを生成", 
            command=self.generate_variations,
            state="disabled",
            font=self.button_font
        )
        self.btn_generate.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.progress_bar = ctk.CTkProgressBar(action_group)
        self.progress_bar.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(action_group, textvariable=self.status_var, font=self.default_font)
        self.status_label.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
    
    def on_rgb_change(self, *args):
        # RGB値が変更されたら自動的にプレビューを更新し、ラベルを更新
        self.r_label.configure(text=f"{self.r_scale.get():.1f}")
        self.g_label.configure(text=f"{self.g_scale.get():.1f}")
        self.b_label.configure(text=f"{self.b_scale.get():.1f}")
        
        if self.original_cv_image is not None:
            self.update_preview()
    
    def drop(self, event):
        file_path = event.data
        
        # Windows のパス形式修正 ('{path}' → path)
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        
        # 複数ファイルの場合は最初のファイルのみ処理
        if " " in file_path:
            file_path = file_path.split(" ")[0]
        
        self.load_image(file_path)
    
    def browse_file(self):
        file_types = [('画像ファイル', '*.png;*.jpg;*.jpeg')]
        file_path = filedialog.askopenfilename(filetypes=file_types)
        if file_path:
            self.load_image(file_path)
    
    def browse_output_dir(self):
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir.set(output_dir)
    
    def load_image(self, file_path):
        try:
            # Pillowで画像を読み込み
            pil_image = Image.open(file_path)
            # OpenCVで画像を読み込み
            self.original_cv_image = cv2.imread(file_path)
            
            if self.original_cv_image is None:
                # OpenCVが直接読み込めない場合（日本語パスなど）
                np_image = np.array(pil_image)
                if len(np_image.shape) == 3 and np_image.shape[2] == 4:  # アルファチャンネルがある場合
                    np_image = cv2.cvtColor(np_image, cv2.COLOR_RGBA2BGR)
                elif len(np_image.shape) == 3 and np_image.shape[2] == 3:  # RGBの場合
                    np_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
                self.original_cv_image = np_image
            
            # 入力パスの設定
            self.input_image_path.set(file_path)
            
            # 出力先フォルダ名を生成（ファイル名_variation_番号）
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            parent_dir = os.path.dirname(file_path)
            output_dir = self.generate_unique_folder_name(parent_dir, base_name)
            self.output_dir.set(output_dir)
            
            # 元画像を保存
            self.original_image = self.original_cv_image.copy()
            
            # プレビューを更新
            self.update_preview()
            
            # 生成ボタンを有効化
            self.btn_generate.configure(state="normal")
            
            # ドロップテキストを非表示
            self.drop_text.place_forget()
            
        except Exception as e:
            messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {str(e)}")
    
    def generate_unique_folder_name(self, parent_dir, base_name):
        # ファイル名_variation_番号 形式のフォルダ名を生成
        folder_base = f"{base_name}_variation"
        counter = 1
        
        while True:
            folder_name = f"{folder_base}_{counter}"
            full_path = os.path.join(parent_dir, folder_name)
            
            if not os.path.exists(full_path):
                return full_path
            
            counter += 1
    
    def update_preview(self):
        if self.original_cv_image is None:
            return
        
        try:
            # RGB強度を適用
            adjusted_image = self.apply_rgb_adjustment(self.original_cv_image.copy())
            
            # プレビュー用に画像をリサイズ
            height, width = adjusted_image.shape[:2]
            max_preview_size = 400
            
            if width > height:
                new_width = max_preview_size
                new_height = int(height * (max_preview_size / width))
            else:
                new_height = max_preview_size
                new_width = int(width * (max_preview_size / height))
            
            resized = cv2.resize(adjusted_image, (new_width, new_height))
            
            # OpenCV画像をPIL画像に変換
            resized_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(resized_rgb)
            
            # CTkImageに変換してラベルに表示
            self.preview_image = ctk.CTkImage(pil_image, size=(new_width, new_height))
            self.preview_label.configure(image=self.preview_image, text="")
            
        except Exception as e:
            messagebox.showerror("エラー", f"プレビューの更新に失敗しました: {str(e)}")
    
    def apply_rgb_adjustment(self, image):
        # チャンネルを分離
        b, g, r = cv2.split(image)
        
        # RGB強度を適用 (0.0-2.0のスケール)
        r = cv2.multiply(r, self.r_scale.get())
        g = cv2.multiply(g, self.g_scale.get())
        b = cv2.multiply(b, self.b_scale.get())
        
        # 値を0-255の範囲に制限
        r = np.clip(r, 0, 255).astype(np.uint8)
        g = np.clip(g, 0, 255).astype(np.uint8)
        b = np.clip(b, 0, 255).astype(np.uint8)
        
        # チャンネルを結合
        return cv2.merge([b, g, r])
    
    def generate_variations(self):
        if self.original_cv_image is None:
            messagebox.showerror("エラー", "画像が読み込まれていません")
            return
        
        # 出力先ディレクトリの確認
        output_dir = self.output_dir.get()
        if not output_dir:
            messagebox.showerror("エラー", "出力先フォルダが指定されていません")
            return
        
        # 出力先ディレクトリの作成
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("エラー", f"出力先フォルダの作成に失敗しました: {str(e)}")
            return
        
        # パラメータの取得
        hue_var_count = self.hue_variations.get()
        sat_var_count = self.saturation_variations.get()
        
        # UIの状態を更新
        self.btn_generate.configure(state="disabled")
        self.status_var.set("処理中...")
        self.progress_bar.set(0)
        
        # 非同期で処理を実行
        thread = threading.Thread(target=self.process_variations, args=(output_dir, hue_var_count, sat_var_count))
        thread.daemon = True  # メインプログラムが終了したらスレッドも終了
        thread.start()
    
    def process_variations(self, output_dir, hue_var_count, sat_var_count):
        try:
            # RGB強度を適用した画像を取得
            adjusted_image = self.apply_rgb_adjustment(self.original_cv_image.copy())
            
            # 出力フォルダの作成
            variations_folder = os.path.join(output_dir, "variations")
            os.makedirs(variations_folder, exist_ok=True)
            
            # BGRからHSVに変換
            hsv_image = cv2.cvtColor(adjusted_image, cv2.COLOR_BGR2HSV)
            
            total_variations = hue_var_count * sat_var_count + 1  # 全組み合わせ + 元画像
            processed_count = 0
            
            # 元のRGB調整した画像を保存
            input_filename = os.path.basename(self.input_image_path.get())
            base_name, ext = os.path.splitext(input_filename)
            
            output_filename = f"{base_name}_original{ext}"
            output_path = os.path.join(output_dir, output_filename)
            cv2.imwrite(output_path, adjusted_image)
            
            processed_count += 1
            self.update_progress(processed_count / total_variations)
            
            # 色相と彩度の全組み合わせを生成
            hue_step = 180 / hue_var_count  # 色相範囲は0-180（OpenCVのHSV空間）
            
            for h in range(hue_var_count):
                hue_shift = int(h * hue_step)
                
                for s in range(sat_var_count):
                    # 彩度の調整
                    sat_factor = (s + 1) / sat_var_count
                    
                    # 色相と彩度を組み合わせて調整
                    hsv_adjusted = hsv_image.copy()
                    hsv_adjusted[:, :, 0] = (hsv_adjusted[:, :, 0] + hue_shift) % 180  # 色相シフト
                    
                    # 彩度調整: sat_factorを掛け算
                    # OpenCVのHSV空間では彩度は0-255
                    hsv_adjusted[:, :, 1] = np.clip(hsv_adjusted[:, :, 1] * sat_factor, 0, 255).astype(np.uint8)
                    
                    bgr_adjusted = cv2.cvtColor(hsv_adjusted, cv2.COLOR_HSV2BGR)
                    
                    # 調整画像を保存
                    output_filename = f"{base_name}_hue_{hue_shift}_sat_{int(sat_factor*100)}{ext}"
                    output_path = os.path.join(variations_folder, output_filename)
                    cv2.imwrite(output_path, bgr_adjusted)
                    
                    processed_count += 1
                    self.update_progress(processed_count / total_variations)

            # 処理完了
            self.complete()
            self.status_var.set("完了")
            
        except Exception as e:
            self.after(0, lambda: self.processing_failed(str(e)))
    
    def update_progress(self, value):
        self.after(0, lambda: self.progress_bar.set(value))
    
    def open_folder(self, folder_path):
        """指定されたフォルダを開く"""
        if os.path.exists(folder_path):
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{folder_path}"')
            else:  # Linux
                os.system(f'xdg-open "{folder_path}"')
        else:
            messagebox.showerror("エラー", f"フォルダが見つかりません: {folder_path}")
    
    def processing_failed(self, error_message):
        """処理失敗時の処理"""
        self.btn_generate.configure(state="normal")
        self.status_var.set("エラー")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました: {error_message}")

    def complete(self):
        self.btn_generate.configure(state="normal")
        self.status_var.set("完了") 

if __name__ == "__main__":
    app = ImageVariationGenerator()
    app.mainloop()


