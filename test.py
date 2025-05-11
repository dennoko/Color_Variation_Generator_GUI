import os
import sys
import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD

class EdgeDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("エッジ検出アプリケーション")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        # 変数の初期化
        self.input_image_path = None
        self.original_image = None
        self.processed_image = None
        self.current_preview = None
        self.padding = 1  # フィルター適用時のパディングサイズ
        
        # エッジ検出パラメータの初期化
        self.brightness_threshold = tk.IntVar(value=30)
        self.r_threshold = tk.IntVar(value=30)
        self.g_threshold = tk.IntVar(value=30)
        self.b_threshold = tk.IntVar(value=30)
        self.brightness_enabled = tk.BooleanVar(value=True)
        self.r_enabled = tk.BooleanVar(value=True)
        self.g_enabled = tk.BooleanVar(value=True)
        self.b_enabled = tk.BooleanVar(value=True)
        self.edge_thickness = tk.IntVar(value=1)
        self.preview_scale = tk.DoubleVar(value=1.0)
        
        # UIの構築
        self.create_ui()
        
        # ドラッグ&ドロップの設定
        self.setup_drag_drop()
        
        # ステータスバーを更新
        self.update_status("ファイルをドラッグ&ドロップするか、「開く」ボタンをクリックしてください。")
    
    def create_ui(self):
        # メインフレームの作成
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 上部フレーム - コントロール
        control_frame = ttk.LabelFrame(main_frame, text="コントロールパネル")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # ファイル操作ボタン
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_frame, text="開く", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="保存", command=self.save_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="リセット", command=self.reset_parameters).pack(side=tk.LEFT, padx=5)
        
        # パラメータ調整フレーム
        param_frame = ttk.Frame(control_frame)
        param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 左側パラメータ (明度、R)
        left_param = ttk.Frame(param_frame)
        left_param.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 明度エッジ検出
        bright_frame = ttk.Frame(left_param)
        bright_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(bright_frame, text="明度エッジ検出", variable=self.brightness_enabled, 
                       command=self.update_preview).pack(side=tk.LEFT)
        ttk.Label(bright_frame, text="閾値:").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Scale(bright_frame, from_=0, to=255, variable=self.brightness_threshold, 
                 command=lambda _: self.update_preview()).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(bright_frame, textvariable=self.brightness_threshold).pack(side=tk.LEFT, padx=5)
        
        # Rチャンネルエッジ検出
        r_frame = ttk.Frame(left_param)
        r_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(r_frame, text="Rチャンネルエッジ検出", variable=self.r_enabled, 
                       command=self.update_preview).pack(side=tk.LEFT)
        ttk.Label(r_frame, text="閾値:").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Scale(r_frame, from_=0, to=255, variable=self.r_threshold, 
                 command=lambda _: self.update_preview()).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(r_frame, textvariable=self.r_threshold).pack(side=tk.LEFT, padx=5)
        
        # 右側パラメータ (G, B)
        right_param = ttk.Frame(param_frame)
        right_param.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Gチャンネルエッジ検出
        g_frame = ttk.Frame(right_param)
        g_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(g_frame, text="Gチャンネルエッジ検出", variable=self.g_enabled, 
                       command=self.update_preview).pack(side=tk.LEFT)
        ttk.Label(g_frame, text="閾値:").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Scale(g_frame, from_=0, to=255, variable=self.g_threshold, 
                 command=lambda _: self.update_preview()).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(g_frame, textvariable=self.g_threshold).pack(side=tk.LEFT, padx=5)
        
        # Bチャンネルエッジ検出
        b_frame = ttk.Frame(right_param)
        b_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(b_frame, text="Bチャンネルエッジ検出", variable=self.b_enabled, 
                       command=self.update_preview).pack(side=tk.LEFT)
        ttk.Label(b_frame, text="閾値:").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Scale(b_frame, from_=0, to=255, variable=self.b_threshold, 
                 command=lambda _: self.update_preview()).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(b_frame, textvariable=self.b_threshold).pack(side=tk.LEFT, padx=5)
        
        # 追加設定フレーム
        additional_frame = ttk.Frame(control_frame)
        additional_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # エッジの太さ
        thickness_frame = ttk.Frame(additional_frame)
        thickness_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(thickness_frame, text="エッジの太さ:").pack(side=tk.LEFT)
        ttk.Scale(thickness_frame, from_=1, to=5, variable=self.edge_thickness, 
                 command=lambda _: self.update_preview()).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(thickness_frame, textvariable=self.edge_thickness).pack(side=tk.LEFT, padx=5)
        
        # プレビュースケール
        scale_frame = ttk.Frame(additional_frame)
        scale_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(scale_frame, text="プレビュースケール:").pack(side=tk.LEFT)
        ttk.Scale(scale_frame, from_=0.1, to=2.0, variable=self.preview_scale, 
                 command=lambda _: self.update_preview()).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(scale_frame, text=lambda: f"{self.preview_scale.get():.1f}").pack(side=tk.LEFT, padx=5)
        
        # 画像表示フレーム
        self.image_frame = ttk.Frame(main_frame)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 元画像表示ラベル
        self.original_frame = ttk.LabelFrame(self.image_frame, text="元画像")
        self.original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.original_label = ttk.Label(self.original_frame)
        self.original_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 処理後画像表示ラベル
        self.processed_frame = ttk.LabelFrame(self.image_frame, text="処理後画像")
        self.processed_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.processed_label = ttk.Label(self.processed_frame)
        self.processed_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ステータスバー
        self.status_bar = ttk.Label(self.root, text="準備完了", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_drag_drop(self):
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.drop)
    
    def drop(self, event):
        file_path = event.data
        # Windows形式のパス修正
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        # 引用符を削除
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]
        
        self.load_image(file_path)
    
    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("画像ファイル", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if file_path:
            self.load_image(file_path)
    
    def load_image(self, file_path):
        try:
            # PillowでRGBに変換して読み込み（日本語パスに対応）
            pil_image = Image.open(file_path).convert('RGB')
            self.input_image_path = file_path

            # opencvで使用するためにBGRに変換
            pil_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # NumPy配列に変換
            self.original_image = np.array(pil_image)
            
            # プレビュー更新
            self.update_preview()
            
            # ステータス更新
            self.update_status(f"画像を読み込みました: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {str(e)}")
            self.update_status(f"エラー: {str(e)}")
    
    def update_preview(self):
        if self.original_image is None:
            return
        
        try:
            # エッジ検出処理
            self.processed_image = self.detect_edges(self.original_image)
            
            # 表示用に準備
            scale = self.preview_scale.get()
            
            # 元画像の表示
            original_resized = cv2.resize(
                self.original_image, 
                (int(self.original_image.shape[1] * scale), int(self.original_image.shape[0] * scale))
            )
            original_pil = Image.fromarray(cv2.cvtColor(original_resized, cv2.COLOR_BGR2RGB))
            original_tk = ImageTk.PhotoImage(original_pil)
            self.original_label.config(image=original_tk)
            self.original_label.image = original_tk
            
            # 処理後画像の表示
            processed_resized = cv2.resize(
                self.processed_image, 
                (int(self.processed_image.shape[1] * scale), int(self.processed_image.shape[0] * scale))
            )
            processed_pil = Image.fromarray(processed_resized)
            processed_tk = ImageTk.PhotoImage(processed_pil)
            self.processed_label.config(image=processed_tk)
            self.processed_label.image = processed_tk
            
            self.update_status("プレビューを更新しました")
        except Exception as e:
            messagebox.showerror("エラー", f"プレビュー更新に失敗しました: {str(e)}")
            self.update_status(f"エラー: {str(e)}")
    
    def detect_edges(self, image):
        # 画像の各チャンネルを取得
        b, g, r = cv2.split(image)
        
        # 明度の計算（輝度計算）
        brightness = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # エッジ検出用の空の画像を作成
        height, width = image.shape[:2]
        edge_image = np.zeros((height, width), dtype=np.uint8)
        
        # エッジ検出の閾値を取得
        bright_thresh = self.brightness_threshold.get()
        r_thresh = self.r_threshold.get()
        g_thresh = self.g_threshold.get()
        b_thresh = self.b_threshold.get()
        
        # パディングサイズ
        pad = self.padding
        thick = self.edge_thickness.get()
        
        # 明度ベースのエッジ検出
        if self.brightness_enabled.get():
            brightness_padded = cv2.copyMakeBorder(brightness, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
            sobel_x = cv2.Sobel(brightness_padded, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(brightness_padded, cv2.CV_64F, 0, 1, ksize=3)
            # パディング部分を削除
            sobel_x = sobel_x[pad:-pad, pad:-pad]
            sobel_y = sobel_y[pad:-pad, pad:-pad]
            
            # 勾配の大きさを計算
            magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
            # 閾値を適用
            bright_edge = np.uint8(magnitude > bright_thresh) * 255
            
            # エッジの太さを調整
            if thick > 1:
                kernel = np.ones((thick, thick), np.uint8)
                bright_edge = cv2.dilate(bright_edge, kernel, iterations=1)
            
            # 結果を合成
            edge_image = cv2.bitwise_or(edge_image, bright_edge)
        
        # Rチャンネルベースのエッジ検出
        if self.r_enabled.get():
            r_padded = cv2.copyMakeBorder(r, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
            sobel_x = cv2.Sobel(r_padded, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(r_padded, cv2.CV_64F, 0, 1, ksize=3)
            sobel_x = sobel_x[pad:-pad, pad:-pad]
            sobel_y = sobel_y[pad:-pad, pad:-pad]
            
            magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
            r_edge = np.uint8(magnitude > r_thresh) * 255
            
            if thick > 1:
                kernel = np.ones((thick, thick), np.uint8)
                r_edge = cv2.dilate(r_edge, kernel, iterations=1)
            
            edge_image = cv2.bitwise_or(edge_image, r_edge)
        
        # Gチャンネルベースのエッジ検出
        if self.g_enabled.get():
            g_padded = cv2.copyMakeBorder(g, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
            sobel_x = cv2.Sobel(g_padded, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(g_padded, cv2.CV_64F, 0, 1, ksize=3)
            sobel_x = sobel_x[pad:-pad, pad:-pad]
            sobel_y = sobel_y[pad:-pad, pad:-pad]
            
            magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
            g_edge = np.uint8(magnitude > g_thresh) * 255
            
            if thick > 1:
                kernel = np.ones((thick, thick), np.uint8)
                g_edge = cv2.dilate(g_edge, kernel, iterations=1)
            
            edge_image = cv2.bitwise_or(edge_image, g_edge)
        
        # Bチャンネルベースのエッジ検出
        if self.b_enabled.get():
            b_padded = cv2.copyMakeBorder(b, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
            sobel_x = cv2.Sobel(b_padded, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(b_padded, cv2.CV_64F, 0, 1, ksize=3)
            sobel_x = sobel_x[pad:-pad, pad:-pad]
            sobel_y = sobel_y[pad:-pad, pad:-pad]
            
            magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
            b_edge = np.uint8(magnitude > b_thresh) * 255
            
            if thick > 1:
                kernel = np.ones((thick, thick), np.uint8)
                b_edge = cv2.dilate(b_edge, kernel, iterations=1)
            
            edge_image = cv2.bitwise_or(edge_image, b_edge)

        # invert black and white
        edge_image = cv2.bitwise_not(edge_image)
        
        return edge_image
    
    def save_image(self):
        if self.processed_image is None:
            messagebox.showinfo("情報", "保存する画像がありません。")
            return
        
        try:
            # 入力画像と同じディレクトリに「edge」フォルダを作成
            input_dir = os.path.dirname(self.input_image_path)
            edge_dir = os.path.join(input_dir, "edge")
            os.makedirs(edge_dir, exist_ok=True)
            
            # ファイル名の作成
            base_name = os.path.splitext(os.path.basename(self.input_image_path))[0]
            
            # 連番ファイル名を生成
            counter = 1
            while True:
                file_name = f"{base_name}_{counter:03d}.png"
                output_path = os.path.join(edge_dir, file_name)
                if not os.path.exists(output_path):
                    break
                counter += 1
            
            # 画像を保存
            cv2.imwrite(output_path, self.processed_image)
            
            self.update_status(f"画像を保存しました: {output_path}")
            messagebox.showinfo("保存完了", f"画像を保存しました:\n{output_path}")
        except Exception as e:
            messagebox.showerror("エラー", f"画像の保存に失敗しました: {str(e)}")
            self.update_status(f"エラー: {str(e)}")
    
    def reset_parameters(self):
        # パラメータをリセット
        self.brightness_threshold.set(30)
        self.r_threshold.set(30)
        self.g_threshold.set(30)
        self.b_threshold.set(30)
        self.brightness_enabled.set(True)
        self.r_enabled.set(True)
        self.g_enabled.set(True)
        self.b_enabled.set(True)
        self.edge_thickness.set(1)
        self.preview_scale.set(1.0)
        
        # プレビュー更新
        self.update_preview()
        
        self.update_status("パラメータをリセットしました")
    
    def update_status(self, message):
        self.status_bar.config(text=message)


def main():
    # Tkinterのルートウィンドウを作成
    root = TkinterDnD.Tk()
    
    # アプリケーションの起動
    app = EdgeDetectionApp(root)
    
    # Tkinterのメインループを開始
    root.mainloop()


if __name__ == "__main__":
    main()