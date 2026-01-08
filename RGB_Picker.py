import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib import cm

class PDFColorPickerApp:
    def __init__(self, master):
        self.master = master
        master.title("PDF/Image Heatmap Picker")
        self.master.geometry("900x600")

        self.file_path = None
        self.doc = None
        self.current_page = 0
        self.img = None
        self.colorbar_min = 0.0
        self.colorbar_max = 1.0
        self.cmap_name = 'viridis'
        self.dpi = 300
        self.picking = False
        self.data_points = []

        # ===== Control Panel =====
        self.control_frame = tk.Frame(master)
        self.control_frame.pack(side=tk.TOP, fill=tk.X)

        self.controls = []

        self.controls.append(tk.Button(self.control_frame, text="Load File", command=self.load_file))

        self.controls.append(tk.Label(self.control_frame, text="Page:"))
        self.page_entry = tk.Entry(self.control_frame, width=5)
        self.controls.append(self.page_entry)

        self.controls.append(tk.Button(self.control_frame, text="Show", command=self.show_page))

        self.controls.append(tk.Label(self.control_frame, text="vmin:"))
        self.min_entry = tk.Entry(self.control_frame, width=6)
        self.controls.append(self.min_entry)

        self.controls.append(tk.Label(self.control_frame, text="vmax:"))
        self.max_entry = tk.Entry(self.control_frame, width=6)
        self.controls.append(self.max_entry)

        self.controls.append(tk.Label(self.control_frame, text="cmap:"))
        self.cmap_entry = tk.Entry(self.control_frame, width=10)
        self.controls.append(self.cmap_entry)

        self.controls.append(tk.Label(self.control_frame, text="dpi:"))
        self.dpi_entry = tk.Entry(self.control_frame, width=6)
        self.controls.append(self.dpi_entry)

        self.controls.append(tk.Button(self.control_frame, text="Start Pick", command=self.start_pick))
        self.controls.append(tk.Button(self.control_frame, text="Stop Pick", command=self.stop_pick))
        self.controls.append(tk.Button(self.control_frame, text="Clear Data", command=self.clear_data))
        self.controls.append(tk.Button(self.control_frame, text="Save TXT", command=self.save_data))
        self.controls.append(tk.Button(self.control_frame, text="Exit", command=self.exit_app))

        # 默认值
        self.page_entry.insert(0, "1")
        self.min_entry.insert(0, "0")
        self.max_entry.insert(0, "100")
        self.cmap_entry.insert(0, "viridis")
        self.dpi_entry.insert(0, str(self.dpi))

        # 防抖绑定
        self._resize_after_id = None
        self._last_per_row = None
        self.master.bind("<Configure>", self.on_resize)

        self.layout_controls()

        # ===== Info Panel =====
        self.info_label = tk.Label(master, text="Points: 0 | No data", anchor="w", justify="left", font=("Courier", 10))
        self.info_label.pack(side=tk.TOP, fill=tk.X)

        # ===== Matplotlib Figure =====
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.fig.canvas.mpl_connect("button_press_event", self.on_click)

    def layout_controls(self):
        """根据窗口宽度动态调整按钮布局"""
        width = self.master.winfo_width()
        if width <= 1:
            return
        avg_width = 90
        per_row = max(1, width // avg_width)
        if self._last_per_row == per_row:
            return
        self._last_per_row = per_row
        for widget in self.controls:
            widget.grid_forget()
        row, col = 0, 0
        for widget in self.controls:
            widget.grid(row=row, column=col, padx=2, pady=2, sticky="w")
            col += 1
            if col >= per_row:
                row += 1
                col = 0

    def on_resize(self, event):
        if self._resize_after_id:
            self.master.after_cancel(self._resize_after_id)
        self._resize_after_id = self.master.after(100, self.layout_controls)

    def load_file(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Supported files", "*.pdf;*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                ("PDF files", "*.pdf"),
                ("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")
            ]
        )
        if not path:
            return
        ext = path.lower().split(".")[-1]
        self.file_path = path
        if ext == "pdf":
            # PDF加载
            self.doc = fitz.open(self.file_path)
            self.current_page = 0
            self.page_entry.delete(0, tk.END)
            self.page_entry.insert(0, "1")
            self.show_page()
        elif ext in ["png", "jpg", "jpeg", "bmp", "gif"]:
            # 图片加载
            self.doc = None
            try:
                self.img = Image.open(self.file_path).convert("RGB")
                self.ax.clear()
                self.ax.imshow(self.img)
                self.ax.set_title(f"Image: {self.file_path.split('/')[-1]}")
                self.canvas.draw()
                self.info_label.config(text="Points: 0 | Image loaded")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
        else:
            messagebox.showerror("Error", "Unsupported file type")

    def show_page(self):
        if self.doc is None:
            messagebox.showinfo("Info", "Current file is an image, no pages to display")
            return
        try:
            page_num = int(self.page_entry.get()) - 1
            if page_num < 0 or page_num >= len(self.doc):
                messagebox.showerror("Error", "Page number out of range")
                return
            self.current_page = page_num
            try:
                self.dpi = int(self.dpi_entry.get())
            except:
                self.dpi = 300
                self.dpi_entry.delete(0, tk.END)
                self.dpi_entry.insert(0, str(self.dpi))
            page = self.doc[page_num]
            pix = page.get_pixmap(dpi=self.dpi)
            self.img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.ax.clear()
            self.ax.imshow(self.img)
            self.ax.set_title(f"PDF Page {page_num+1} (dpi={self.dpi})")
            self.canvas.draw()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def start_pick(self):
        try:
            self.colorbar_min = float(self.min_entry.get())
            self.colorbar_max = float(self.max_entry.get())
            self.cmap_name = self.cmap_entry.get()
        except:
            messagebox.showerror("Error", "Invalid colorbar range")
            return
        self.picking = True
        self.info_label.config(text=f"Points: {len(self.data_points)} | Picking mode ON")

    def stop_pick(self):
        self.picking = False
        self.info_label.config(text=f"Points: {len(self.data_points)} | Picking mode OFF")

    def clear_data(self):
        self.data_points.clear()
        self.picking = False
        self.info_label.config(text="Points: 0 | No data")
        messagebox.showinfo("Info", "Data cleared")

    def exit_app(self):
        plt.close('all')
        self.master.quit()
        self.master.destroy()


    def on_click(self, event):
        if not self.picking or not event.inaxes:
            return
        try:
            x, y = int(event.xdata), int(event.ydata)
            rgb = np.array(self.img)[y, x] / 255.0
            heat_value = self.rgb_to_value(rgb)
            self.data_points.append((
                x, y,
                int(rgb[0]*255),
                int(rgb[1]*255),
                int(rgb[2]*255),
                heat_value
            ))
            point_count = len(self.data_points)
            self.info_label.config(
                text=f"Points: {point_count} | Last: x={x} y={y} "
                     f"RGB={tuple(int(c*255) for c in rgb)} Value={heat_value:.2f}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Click error: {e}")

    def rgb_to_value(self, target_rgb):
        cmap = cm.get_cmap(self.cmap_name)
        vmin, vmax = self.colorbar_min, self.colorbar_max
        samples = np.linspace(0, 1, 10000)
        colors = cmap(samples)[:, :3]
        dist = np.linalg.norm(colors - target_rgb, axis=1)
        best_index = np.argmin(dist)
        best_norm_value = samples[best_index]
        best_actual_value = vmin + best_norm_value * (vmax - vmin)
        return best_actual_value

    def save_data(self):
        if not self.data_points:
            messagebox.showerror("Error", "No data to save")
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text files", "*.txt")])
        if save_path:
            with open(save_path, "w") as f:
                f.write("x\ty\tR\tG\tB\tValue\n")
                for dp in self.data_points:
                    f.write("\t".join(map(str, dp)) + "\n")
            messagebox.showinfo("Info", f"Data saved to {save_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFColorPickerApp(root)
    root.mainloop()
