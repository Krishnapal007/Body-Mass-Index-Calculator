"""
main.py
-------
BMI Health Tracker - Advanced Edition (Tkinter dashboard).

Run with:  python main.py
"""

import csv
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import bmi_calculator as bmi
import visualization as viz
from database import Database, DatabaseError, export_records_to_csv

# --------------------------------------------------------------------------- #
# Theme
# --------------------------------------------------------------------------- #
C = {
    "sidebar": "#0F172A", "sidebar_hover": "#1E293B", "sidebar_text": "#CBD5E1",
    "bg": "#F1F5F9", "card": "#FFFFFF", "border": "#E2E8F0",
    "primary": "#4F46E5", "text": "#0F172A", "muted": "#64748B",
    "success": "#16A34A", "danger": "#DC2626", "secondary": "#64748B",
    "input": "#F8FAFC",
}
FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 9)


# --------------------------------------------------------------------------- #
# Reusable UI helpers
# --------------------------------------------------------------------------- #
def darken(hex_color, factor=0.85):
    """Return a darker shade of a hex colour (used for hover effects)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


def make_button(parent, text, command, bg=None, fg="white", padx=18, pady=9):
    """Flat button with hover effect."""
    bg = bg or C["primary"]
    hover = darken(bg)
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                    activebackground=hover, activeforeground=fg, font=FONT_BOLD,
                    relief="flat", bd=0, padx=padx, pady=pady, cursor="hand2")
    btn.bind("<Enter>", lambda _e: btn.config(bg=hover))
    btn.bind("<Leave>", lambda _e: btn.config(bg=bg))
    return btn


def make_card(parent):
    """White bordered container."""
    return tk.Frame(parent, bg=C["card"], highlightbackground=C["border"],
                    highlightthickness=1)


def make_entry(parent, variable):
    return tk.Entry(parent, textvariable=variable, font=("Segoe UI", 12), relief="flat",
                    bg=C["input"], fg=C["text"], insertbackground=C["text"],
                    highlightthickness=1, highlightbackground=C["border"],
                    highlightcolor=C["primary"])


def page_header(parent, title, subtitle):
    frame = tk.Frame(parent, bg=C["bg"])
    frame.pack(fill="x", padx=30, pady=(24, 12))
    tk.Label(frame, text=title, font=("Segoe UI", 22, "bold"),
             bg=C["bg"], fg=C["text"]).pack(anchor="w")
    tk.Label(frame, text=subtitle, font=FONT, bg=C["bg"], fg=C["muted"]).pack(anchor="w")


def make_tree(parent, columns, height=10):
    """Create a scrollable Treeview. columns = [(key, heading, width, anchor)]."""
    frame = tk.Frame(parent, bg=C["card"])
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings",
                        height=height, selectmode="extended")
    for key, heading, width, anchor in columns:
        tree.heading(key, text=heading)
        tree.column(key, width=width, anchor=anchor, minwidth=50)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    for category, tint in bmi.CATEGORY_TINTS.items():
        tree.tag_configure(category, background=tint)
    return frame, tree


def show_figure(container, fig):
    """Embed a Matplotlib figure in a Tk container (replacing previous content)."""
    for child in container.winfo_children():
        child.destroy()
    canvas = FigureCanvasTkAgg(fig, master=container)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    return canvas


def show_placeholder(container, text):
    for child in container.winfo_children():
        child.destroy()
    tk.Label(container, text=text, font=FONT, bg=C["card"], fg=C["muted"],
             justify="center").pack(expand=True)


def record_values(r):
    """Row values for the history table."""
    return (r["id"], r["username"], f"{r['weight']:.2f}", f"{r['height']:.2f}",
            f"{r['bmi']:.2f}", r["category"], r["recorded_at"])


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
class DashboardPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        page_header(self, "Dashboard", "Overview of all BMI records stored in your database")

        stats = tk.Frame(self, bg=C["bg"])
        stats.pack(fill="x", padx=30)
        self.values = {}
        specs = [("records", "Total Records", C["primary"]),
                 ("users", "Total Users", "#0891B2"),
                 ("average", "Average BMI", "#F59E0B"),
                 ("latest", "Latest Category", C["success"])]
        for col, (key, title, accent) in enumerate(specs):
            stats.columnconfigure(col, weight=1, uniform="stat")
            card = make_card(stats)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
            tk.Frame(card, bg=accent, height=4).pack(fill="x")
            tk.Label(card, text=title, font=FONT, bg=C["card"],
                     fg=C["muted"]).pack(anchor="w", padx=16, pady=(12, 0))
            self.values[key] = tk.Label(card, text="-", font=("Segoe UI", 24, "bold"),
                                        bg=C["card"], fg=C["text"])
            self.values[key].pack(anchor="w", padx=16, pady=(0, 14))

        lower = tk.Frame(self, bg=C["bg"])
        lower.pack(fill="both", expand=True, padx=30, pady=(16, 8))
        lower.columnconfigure(0, weight=3, uniform="low")
        lower.columnconfigure(1, weight=2, uniform="low")
        lower.rowconfigure(0, weight=1)

        left = make_card(lower)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(left, text="Recent Records", font=("Segoe UI", 13, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w", padx=16, pady=(14, 8))
        columns = [("user", "Username", 130, "w"), ("weight", "Weight (kg)", 90, "center"),
                   ("bmi", "BMI", 70, "center"), ("cat", "Category", 100, "center"),
                   ("date", "Date and Time", 150, "center")]
        frame, self.tree = make_tree(left, columns, height=8)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        right = make_card(lower)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(right, text="Category Distribution", font=("Segoe UI", 13, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w", padx=16, pady=(14, 0))
        self.chart_holder = tk.Frame(right, bg=C["card"])
        self.chart_holder.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh(self, username=None):
        db = self.app.db
        try:
            total = db.count_records()
            users = db.count_users()
            average = db.get_average_bmi()
            latest = db.get_latest_record()
            recent = db.get_all_records(limit=8)
            counts = db.get_category_counts()
        except DatabaseError as exc:
            self.app.show_error("Database error", str(exc))
            return

        self.values["records"].config(text=str(total))
        self.values["users"].config(text=str(users))
        self.values["average"].config(text=f"{average:.2f}" if average is not None else "-")
        if latest:
            self.values["latest"].config(text=latest["category"],
                                         fg=bmi.get_color(latest["category"]))
        else:
            self.values["latest"].config(text="-", fg=C["text"])

        self.tree.delete(*self.tree.get_children())
        for r in recent:
            self.tree.insert("", "end", iid=str(r["id"]), tags=(r["category"],),
                             values=(r["username"], f"{r['weight']:.2f}", f"{r['bmi']:.2f}",
                                     r["category"], r["recorded_at"]))
        if total == 0:
            show_placeholder(self.chart_holder, "No data yet.\nCalculate a BMI to get started.")
        else:
            try:
                show_figure(self.chart_holder, viz.create_category_figure(counts))
            except viz.GraphError as exc:
                self.app.show_error("Graph error", str(exc))


# --------------------------------------------------------------------------- #
# BMI Calculator
# --------------------------------------------------------------------------- #
class CalculatorPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.user_var = tk.StringVar()
        self.weight_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self._scale_value = None

        page_header(self, "BMI Calculator", "Enter your details to calculate and save your BMI")
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")
        body.rowconfigure(0, weight=1)

        # ---- Input card ----
        form = make_card(body)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        inner = tk.Frame(form, bg=C["card"])
        inner.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(inner, text="Your Details", font=("Segoe UI", 14, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 12))

        self._label(inner, "Username")
        self.user_combo = ttk.Combobox(inner, textvariable=self.user_var, font=("Segoe UI", 12))
        self.user_combo.pack(fill="x", ipady=4)
        self._label(inner, "Weight (kg)")
        self.weight_entry = make_entry(inner, self.weight_var)
        self.weight_entry.pack(fill="x", ipady=6)
        self._label(inner, "Height (meters, e.g. 1.75)")
        self.height_entry = make_entry(inner, self.height_var)
        self.height_entry.pack(fill="x", ipady=6)

        for widget in (self.user_combo, self.weight_entry, self.height_entry):
            widget.bind("<Return>", lambda _e: self.on_calculate())

        make_button(inner, "Calculate BMI", self.on_calculate, pady=11).pack(fill="x", pady=(22, 8))
        row = tk.Frame(inner, bg=C["card"])
        row.pack(fill="x")
        row.columnconfigure(0, weight=1, uniform="b")
        row.columnconfigure(1, weight=1, uniform="b")
        make_button(row, "Clear", self.on_clear, bg=C["secondary"]).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        make_button(row, "Reset", self.on_reset, bg=C["danger"]).grid(
            row=0, column=1, sticky="ew", padx=(4, 0))
        tk.Label(inner, text="Clear empties weight and height.  Reset empties everything.",
                 font=FONT_SMALL, bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(10, 0))

        # ---- Result card ----
        result = make_card(body)
        result.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        res = tk.Frame(result, bg=C["card"])
        res.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(res, text="Your Result", font=("Segoe UI", 14, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        self.res_user = tk.Label(res, text="", font=FONT, bg=C["card"], fg=C["muted"])
        self.res_user.pack(anchor="w", pady=(2, 0))
        self.res_bmi = tk.Label(res, text="--", font=("Segoe UI", 54, "bold"),
                                bg=C["card"], fg=C["muted"])
        self.res_bmi.pack(pady=(10, 0))
        self.res_cat = tk.Label(res, text="Waiting for input", font=("Segoe UI", 18, "bold"),
                                bg=C["card"], fg=C["muted"])
        self.res_cat.pack()
        self.scale = tk.Canvas(res, height=72, bg=C["card"], highlightthickness=0)
        self.scale.pack(fill="x", pady=(16, 4))
        self.scale.bind("<Configure>", lambda _e: self.draw_scale(self._scale_value))
        self.res_note = tk.Label(res, text="", font=FONT, bg=C["card"], fg=C["muted"])
        self.res_note.pack(pady=(4, 0))
        self.res_advice = tk.Label(res, text="Enter your details and press Calculate BMI.",
                                   font=FONT, bg=C["card"], fg=C["text"],
                                   wraplength=380, justify="center")
        self.res_advice.pack(pady=(10, 0))
        tk.Label(res, text=bmi.DISCLAIMER, font=FONT_SMALL, bg=C["card"], fg=C["muted"],
                 wraplength=380, justify="center").pack(side="bottom", pady=(8, 0))

    @staticmethod
    def _label(parent, text):
        tk.Label(parent, text=text, font=FONT_BOLD, bg=C["card"],
                 fg=C["text"]).pack(anchor="w", pady=(12, 4))

    def refresh(self, username=None):
        try:
            self.user_combo["values"] = self.app.db.get_usernames()
        except DatabaseError as exc:
            self.app.show_error("Database error", str(exc))
        self.draw_scale(self._scale_value)

    def draw_scale(self, value):
        """Draw the coloured BMI scale with a marker at the user's BMI."""
        c = self.scale
        c.delete("all")
        width = max(c.winfo_width(), 200)
        margin, low, high = 10, 10.0, 40.0
        span = width - 2 * margin

        def x_at(v):
            return margin + (min(max(v, low), high) - low) / (high - low) * span

        for start, end, name in [(10, 18.5, "Underweight"), (18.5, 25, "Normal"),
                                 (25, 30, "Overweight"), (30, 40, "Obese")]:
            x1, x2 = x_at(start), x_at(end)
            c.create_rectangle(x1, 26, x2, 40, fill=bmi.get_color(name), outline="")
            c.create_text((x1 + x2) / 2, 54, text=name, font=("Segoe UI", 8), fill=C["muted"])
        if value is not None:
            x = x_at(value)
            c.create_polygon(x - 7, 4, x + 7, 4, x, 20, fill=C["text"], outline="")
            c.create_line(x, 20, x, 44, fill=C["text"], width=2)

    def on_calculate(self):
        try:
            username, weight, height = bmi.validate_inputs(
                self.user_var.get(), self.weight_var.get(), self.height_var.get())
        except bmi.ValidationError as exc:
            self.app.show_error("Invalid input", str(exc), warning=True)
            return

        value = bmi.calculate_bmi(weight, height)
        category = bmi.get_category(value)
        db = self.app.db

        note = ""
        try:
            previous = db.get_latest_record(username)
            record_id = db.insert_record(username, weight, height, value, category)
        except DatabaseError as exc:
            self.show_result(username, value, category, "Result could not be saved.")
            self.app.show_error("Database error", str(exc))
            return

        if previous:
            diff = value - previous["bmi"]
            note = f"Previous BMI: {previous['bmi']:.2f}  ({diff:+.2f})"
        else:
            note = "First record for this user."
        self.show_result(username, value, category, note)
        self.refresh()
        self.app.notify(f"BMI {value:.2f} ({category}) saved for {username} "
                        f"- record #{record_id}.", "success")

    def show_result(self, username, value, category, note):
        color = bmi.get_color(category)
        self._scale_value = value
        self.res_user.config(text=f"User: {username}")
        self.res_bmi.config(text=f"{value:.2f}", fg=color)
        self.res_cat.config(text=category, fg=color)
        self.res_note.config(text=note)
        self.res_advice.config(text=bmi.CATEGORY_ADVICE[category])
        self.draw_scale(value)

    def on_clear(self):
        self.weight_var.set("")
        self.height_var.set("")
        self.weight_entry.focus_set()

    def on_reset(self):
        self.user_var.set("")
        self.on_clear()
        self._scale_value = None
        self.res_user.config(text="")
        self.res_bmi.config(text="--", fg=C["muted"])
        self.res_cat.config(text="Waiting for input", fg=C["muted"])
        self.res_note.config(text="")
        self.res_advice.config(text="Enter your details and press Calculate BMI.")
        self.draw_scale(None)
        self.user_combo.focus_set()
        self.app.notify("Form reset.", "info")


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #
class HistoryPage(tk.Frame):
    ALL_CATEGORIES = "All Categories"

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.records = []
        self._exact_user = None
        self.search_var = tk.StringVar()
        self.category_var = tk.StringVar(value=self.ALL_CATEGORIES)

        page_header(self, "BMI History", "Search, filter, edit, delete and export saved records")

        bar = make_card(self)
        bar.pack(fill="x", padx=30)
        top = tk.Frame(bar, bg=C["card"])
        top.pack(fill="x", padx=16, pady=12)
        tk.Label(top, text="Username:", font=FONT_BOLD, bg=C["card"],
                 fg=C["text"]).pack(side="left")
        entry = make_entry(top, self.search_var)
        entry.pack(side="left", padx=(6, 12), ipady=4)
        entry.bind("<Return>", lambda _e: self.load())
        combo = ttk.Combobox(top, textvariable=self.category_var, state="readonly", width=15,
                             values=[self.ALL_CATEGORIES] + bmi.CATEGORY_ORDER)
        combo.pack(side="left", padx=(0, 12))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.load())
        make_button(top, "Search", self.load, pady=6, padx=14).pack(side="left", padx=(0, 6))
        make_button(top, "Clear Filters", self.clear_filters, bg=C["secondary"],
                    pady=6, padx=14).pack(side="left")
        self.search_var.trace_add("write", lambda *_a: self._on_text_change())

        actions = tk.Frame(bar, bg=C["card"])
        actions.pack(fill="x", padx=16, pady=(0, 12))
        make_button(actions, "Refresh", self.load, pady=6, padx=14).pack(side="left", padx=(0, 6))
        make_button(actions, "Edit Selected", self.edit_selected, bg="#0891B2",
                    pady=6, padx=14).pack(side="left", padx=(0, 6))
        make_button(actions, "Delete Selected", self.delete_selected, bg=C["danger"],
                    pady=6, padx=14).pack(side="left", padx=(0, 6))
        make_button(actions, "Export to CSV", self.export_csv, bg=C["success"],
                    pady=6, padx=14).pack(side="left")
        self.count_label = tk.Label(actions, text="", font=FONT_BOLD, bg=C["card"], fg=C["primary"])
        self.count_label.pack(side="right")

        table = make_card(self)
        table.pack(fill="both", expand=True, padx=30, pady=(12, 16))
        columns = [("id", "ID", 60, "center"), ("user", "Username", 160, "w"),
                   ("weight", "Weight (kg)", 100, "center"), ("height", "Height (m)", 100, "center"),
                   ("bmi", "BMI", 80, "center"), ("cat", "Category", 120, "center"),
                   ("date", "Date and Time", 170, "center")]
        frame, self.tree = make_tree(table, columns)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())

    def _on_text_change(self):
        # Typing manually cancels an exact-user filter coming from other pages
        if self._exact_user and self.search_var.get().strip().lower() != self._exact_user.lower():
            self._exact_user = None
        self.load()

    def refresh(self, username=None):
        if username is not None:
            self._exact_user = username
            self.category_var.set(self.ALL_CATEGORIES)
            self.search_var.set(username)  # triggers load via trace
        self.load()

    def clear_filters(self):
        self._exact_user = None
        self.category_var.set(self.ALL_CATEGORIES)
        self.search_var.set("")
        self.load()

    def load(self):
        category = self.category_var.get()
        category = None if category == self.ALL_CATEGORIES else category
        exact = bool(self._exact_user) and \
            self.search_var.get().strip().lower() == self._exact_user.lower()
        try:
            self.records = self.app.db.search_records(self.search_var.get(), category, exact)
            total = self.app.db.count_records()
        except DatabaseError as exc:
            self.app.show_error("Database error", str(exc))
            return
        self.tree.delete(*self.tree.get_children())
        for r in self.records:
            self.tree.insert("", "end", iid=str(r["id"]), tags=(r["category"],),
                             values=record_values(r))
        self.count_label.config(
            text=f"Showing {len(self.records)} of {total} total records")

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.app.show_error("Nothing selected", "Select one or more records to delete.",
                                warning=True)
            return
        if not messagebox.askyesno("Confirm delete",
                                   f"Delete {len(selected)} selected record(s)?\n"
                                   "This cannot be undone."):
            return
        try:
            removed = self.app.db.delete_records([int(i) for i in selected])
        except DatabaseError as exc:
            self.app.show_error("Database error", str(exc))
            return
        self.load()
        self.app.notify(f"Deleted {removed} record(s).", "success")

    def edit_selected(self):
        selected = self.tree.selection()
        if len(selected) != 1:
            self.app.show_error("Edit record", "Select exactly one record to edit.", warning=True)
            return
        try:
            record = self.app.db.get_record(int(selected[0]))
        except DatabaseError as exc:
            self.app.show_error("Database error", str(exc))
            return
        if not record:
            self.load()
            return

        dialog = tk.Toplevel(self)
        dialog.title(f"Edit record #{record['id']}")
        dialog.configure(bg=C["card"])
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        weight_var = tk.StringVar(value=f"{record['weight']:g}")
        height_var = tk.StringVar(value=f"{record['height']:g}")
        body = tk.Frame(dialog, bg=C["card"])
        body.pack(padx=28, pady=22)
        tk.Label(body, text=f"User: {record['username']}", font=FONT_BOLD,
                 bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 6))
        tk.Label(body, text="Weight (kg)", font=FONT, bg=C["card"], fg=C["text"]).pack(anchor="w")
        make_entry(body, weight_var).pack(fill="x", ipady=5, pady=(2, 10))
        tk.Label(body, text="Height (meters)", font=FONT, bg=C["card"], fg=C["text"]).pack(anchor="w")
        make_entry(body, height_var).pack(fill="x", ipady=5, pady=(2, 14))

        def save():
            try:
                weight = bmi.validate_weight(weight_var.get())
                height = bmi.validate_height(height_var.get())
            except bmi.ValidationError as exc:
                messagebox.showwarning("Invalid input", str(exc), parent=dialog)
                return
            value = bmi.calculate_bmi(weight, height)
            try:
                self.app.db.update_record(record["id"], weight, height, value,
                                          bmi.get_category(value))
            except DatabaseError as exc:
                messagebox.showerror("Database error", str(exc), parent=dialog)
                return
            dialog.destroy()
            self.load()
            self.app.notify(f"Record #{record['id']} updated (BMI {value:.2f}).", "success")

        row = tk.Frame(body, bg=C["card"])
        row.pack(fill="x")
        make_button(row, "Save", save, pady=7).pack(side="left", padx=(0, 8))
        make_button(row, "Cancel", dialog.destroy, bg=C["secondary"], pady=7).pack(side="left")

        dialog.update_idletasks()
        root = self.winfo_toplevel()
        x = root.winfo_x() + (root.winfo_width() - dialog.winfo_width()) // 2
        y = root.winfo_y() + (root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()

    def export_csv(self):
        if not self.records:
            self.app.show_error("Export", "There are no records to export.", warning=True)
            return
        default = f"bmi_history_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = filedialog.asksaveasfilename(
            title="Export BMI history", defaultextension=".csv", initialfile=default,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            count = export_records_to_csv(self.records, path)
        except (OSError, csv.Error) as exc:
            self.app.show_error("Export failed",
                                f"Could not write the CSV file.\n\n{exc}\n\n"
                                "Close the file if it is open in Excel and try again.")
            return
        self.app.notify(f"Exported {count} record(s) to {path}", "success")
        messagebox.showinfo("Export complete", f"{count} record(s) exported successfully.")


# --------------------------------------------------------------------------- #
# Analytics
# --------------------------------------------------------------------------- #
class AnalyticsPage(tk.Frame):
    ALL = "All Users"

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.figure = None
        self.user_var = tk.StringVar(value=self.ALL)

        page_header(self, "BMI Analytics", "Date-wise BMI trend graphs for each user")
        bar = make_card(self)
        bar.pack(fill="x", padx=30)
        row = tk.Frame(bar, bg=C["card"])
        row.pack(fill="x", padx=16, pady=12)
        tk.Label(row, text="User:", font=FONT_BOLD, bg=C["card"], fg=C["text"]).pack(side="left")
        self.combo = ttk.Combobox(row, textvariable=self.user_var, state="readonly", width=24)
        self.combo.pack(side="left", padx=(8, 12))
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self.generate())
        make_button(row, "Generate Graph", self.generate, pady=6, padx=14).pack(side="left", padx=(0, 6))
        make_button(row, "Save Graph", self.save_graph, bg=C["success"],
                    pady=6, padx=14).pack(side="left")
        self.stats_label = tk.Label(bar, text="", font=FONT, bg=C["card"], fg=C["muted"])
        self.stats_label.pack(anchor="w", padx=16, pady=(0, 12))

        card = make_card(self)
        card.pack(fill="both", expand=True, padx=30, pady=(12, 16))
        self.chart_holder = tk.Frame(card, bg=C["card"])
        self.chart_holder.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh(self, username=None):
        try:
            users = self.app.db.get_usernames()
        except DatabaseError as exc:
            self.app.show_error("Database error", str(exc))
            return
        self.combo["values"] = [self.ALL] + users
        if username is not None and username in users:
            self.user_var.set(username)
        elif self.user_var.get() not in [self.ALL] + users:
            self.user_var.set(self.ALL)
        self.generate()

    def generate(self):
        selection = self.user_var.get() or self.ALL
        try:
            db = self.app.db
            names = db.get_usernames() if selection == self.ALL else [selection]
            data = {name: db.get_records_by_user(name) for name in names}
            data = {name: rows for name, rows in data.items() if rows}
            if not data:
                self.figure = None
                self.stats_label.config(text="")
                show_placeholder(self.chart_holder,
                                 "No BMI records yet.\nUse the BMI Calculator to add some.")
                return
            self.figure = viz.create_trend_figure(data)
            show_figure(self.chart_holder, self.figure)
            self.stats_label.config(text=self._stats_text(selection, data))
        except (DatabaseError, viz.GraphError) as exc:
            self.figure = None
            self.app.show_error("Graph error", str(exc))
        except Exception as exc:  # unexpected rendering problem
            self.figure = None
            self.app.show_error("Graph error", f"Could not display the graph: {exc}")

    def _stats_text(self, selection, data):
        if selection == self.ALL:
            values = [r["bmi"] for rows in data.values() for r in rows]
            return (f"Users: {len(data)}   |   Records: {len(values)}   |   "
                    f"Average BMI: {sum(values) / len(values):.2f}")
        values = [r["bmi"] for r in next(iter(data.values()))]
        return (f"Records: {len(values)}   |   First: {values[0]:.2f}   |   "
                f"Latest: {values[-1]:.2f}   |   Change: {values[-1] - values[0]:+.2f}   |   "
                f"Min: {min(values):.2f}   |   Max: {max(values):.2f}   |   "
                f"Average: {sum(values) / len(values):.2f}")

    def save_graph(self):
        if self.figure is None:
            self.app.show_error("Save graph", "There is no graph to save yet.", warning=True)
            return
        path = filedialog.asksaveasfilename(
            title="Save graph", defaultextension=".png",
            initialfile=f"bmi_graph_{datetime.now():%Y%m%d_%H%M%S}.png",
            filetypes=[("PNG image", "*.png"), ("PDF file", "*.pdf"), ("SVG image", "*.svg")])
        if not path:
            return
        try:
            viz.save_figure(self.figure, path)
        except viz.GraphError as exc:
            self.app.show_error("Save failed", str(exc))
            return
        self.app.notify(f"Graph saved to {path}", "success")


# --------------------------------------------------------------------------- #
# User management
# --------------------------------------------------------------------------- #
class UsersPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.search_var = tk.StringVar()
        page_header(self, "User Management", "View, inspect and remove users and their records")

        bar = make_card(self)
        bar.pack(fill="x", padx=30)
        row = tk.Frame(bar, bg=C["card"])
        row.pack(fill="x", padx=16, pady=12)
        tk.Label(row, text="Search user:", font=FONT_BOLD, bg=C["card"],
                 fg=C["text"]).pack(side="left")
        make_entry(row, self.search_var).pack(side="left", padx=(8, 12), ipady=4)
        self.search_var.trace_add("write", lambda *_a: self.refresh())
        make_button(row, "View History", self.view_history, pady=6, padx=14).pack(side="left", padx=(0, 6))
        make_button(row, "View Graph", self.view_graph, bg="#0891B2", pady=6, padx=14).pack(side="left", padx=(0, 6))
        make_button(row, "Delete User", self.delete_user, bg=C["danger"], pady=6, padx=14).pack(side="left", padx=(0, 6))
        make_button(row, "Refresh", self.refresh, bg=C["secondary"], pady=6, padx=14).pack(side="left")
        self.count_label = tk.Label(row, text="", font=FONT_BOLD, bg=C["card"], fg=C["primary"])
        self.count_label.pack(side="right")

        card = make_card(self)
        card.pack(fill="both", expand=True, padx=30, pady=(12, 16))
        columns = [("user", "Username", 180, "w"), ("records", "Records", 80, "center"),
                   ("latest", "Latest BMI", 100, "center"), ("cat", "Latest Category", 130, "center"),
                   ("avg", "Average BMI", 110, "center"), ("last", "Last Updated", 170, "center")]
        frame, self.tree = make_tree(card, columns)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.configure(selectmode="browse")
        self.tree.bind("<Double-1>", lambda _e: self.view_history())

    def refresh(self, username=None):
        try:
            summaries = self.app.db.get_user_summaries(self.search_var.get())
            total_users = self.app.db.count_users()
        except DatabaseError as exc:
            self.app.show_error("Database error", str(exc))
            return
        self.tree.delete(*self.tree.get_children())
        for s in summaries:
            self.tree.insert("", "end", iid=s["username"], tags=(s["latest_category"],),
                             values=(s["username"], s["total_records"], f"{s['latest_bmi']:.2f}",
                                     s["latest_category"], f"{s['avg_bmi']:.2f}", s["last_updated"]))
        self.count_label.config(text=f"Showing {len(summaries)} of {total_users} users")

    def _selected_user(self):
        selected = self.tree.selection()
        if not selected:
            self.app.show_error("Select a user", "Please select a user from the list first.",
                                warning=True)
            return None
        return selected[0]

    def view_history(self):
        name = self._selected_user()
        if name:
            self.app.show_page("history", username=name)

    def view_graph(self):
        name = self._selected_user()
        if name:
            self.app.show_page("analytics", username=name)

    def delete_user(self):
        name = self._selected_user()
        if not name:
            return
        if not messagebox.askyesno("Confirm delete",
                                   f"Delete user '{name}' and ALL of their records?\n"
                                   "This cannot be undone."):
            return
        try:
            removed = self.app.db.delete_user(name)
        except DatabaseError as exc:
            self.app.show_error("Database error", str(exc))
            return
        self.refresh()
        self.app.notify(f"Deleted user '{name}' ({removed} records).", "success")


# --------------------------------------------------------------------------- #
# Main application window
# --------------------------------------------------------------------------- #
class App(tk.Tk):
    NAV = [("dashboard", "Dashboard"), ("calculator", "BMI Calculator"),
           ("history", "BMI History"), ("analytics", "BMI Analytics"),
           ("users", "User Management")]

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("BMI Health Tracker - Advanced Edition")
        self.geometry("1240x780")
        self.minsize(1080, 700)
        self.configure(bg=C["bg"])
        self._notify_job = None
        self._setup_styles()

        # Status bar (bottom)
        status = tk.Frame(self, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        status.pack(side="bottom", fill="x")
        self.status_label = tk.Label(status, text="Ready", font=FONT_SMALL, bg=C["card"],
                                     fg=C["muted"], anchor="w")
        self.status_label.pack(side="left", padx=12, pady=5)
        tk.Label(status, text="BMI is a screening tool, not a medical diagnosis.",
                 font=FONT_SMALL, bg=C["card"], fg=C["muted"]).pack(side="right", padx=12)

        # Sidebar
        sidebar = tk.Frame(self, bg=C["sidebar"], width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="BMI Health\nTracker", font=("Segoe UI", 20, "bold"),
                 bg=C["sidebar"], fg="white", justify="left").pack(anchor="w", padx=24, pady=(30, 2))
        tk.Label(sidebar, text="Advanced Edition", font=FONT_SMALL, bg=C["sidebar"],
                 fg="#94A3B8").pack(anchor="w", padx=24, pady=(0, 28))
        self.nav_buttons = {}
        for key, label in self.NAV:
            btn = tk.Button(sidebar, text=f"   {label}", anchor="w", font=FONT_BOLD,
                            bg=C["sidebar"], fg=C["sidebar_text"], relief="flat", bd=0,
                            activebackground=C["primary"], activeforeground="white",
                            cursor="hand2", padx=12, pady=12,
                            command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", padx=12, pady=2)
            btn.bind("<Enter>", lambda _e, b=btn, k=key: self._nav_hover(b, k, True))
            btn.bind("<Leave>", lambda _e, b=btn, k=key: self._nav_hover(b, k, False))
            self.nav_buttons[key] = btn
        make_button(sidebar, "Exit", self.destroy, bg="#334155", pady=9).pack(
            side="bottom", fill="x", padx=16, pady=20)

        # Page container
        container = tk.Frame(self, bg=C["bg"])
        container.pack(side="left", fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.pages = {
            "dashboard": DashboardPage(container, self),
            "calculator": CalculatorPage(container, self),
            "history": HistoryPage(container, self),
            "analytics": AnalyticsPage(container, self),
            "users": UsersPage(container, self),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.current = None
        self.show_page("dashboard")

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", font=FONT, rowheight=30, background="white",
                        fieldbackground="white", foreground=C["text"], borderwidth=0)
        style.configure("Treeview.Heading", font=FONT_BOLD, background="#E2E8F0",
                        foreground=C["text"], relief="flat", padding=6)
        style.map("Treeview", background=[("selected", C["primary"])],
                  foreground=[("selected", "white")])
        style.configure("TCombobox", padding=4)

    def _nav_hover(self, button, key, entering):
        if key == self.current:
            return
        button.config(bg=C["sidebar_hover"] if entering else C["sidebar"])

    def show_page(self, name, username=None):
        """Raise a page, highlight its nav button and refresh its data."""
        self.current = name
        for key, btn in self.nav_buttons.items():
            active = key == name
            btn.config(bg=C["primary"] if active else C["sidebar"],
                       fg="white" if active else C["sidebar_text"])
        page = self.pages[name]
        page.tkraise()
        page.refresh(username)

    # ---- messaging ----
    def notify(self, message, kind="info"):
        """Show a coloured message in the status bar for a few seconds."""
        colors = {"success": C["success"], "error": C["danger"], "info": C["muted"]}
        self.status_label.config(text=message, fg=colors.get(kind, C["muted"]),
                                 font=("Segoe UI", 9, "bold"))
        if self._notify_job:
            self.after_cancel(self._notify_job)
        self._notify_job = self.after(
            8000, lambda: self.status_label.config(text="Ready", fg=C["muted"], font=FONT_SMALL))

    def show_error(self, title, message, warning=False):
        self.notify(message.splitlines()[0], "error")
        (messagebox.showwarning if warning else messagebox.showerror)(title, message)


def main():
    # Sharper text on high-DPI Windows displays
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    try:
        db = Database()
    except DatabaseError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Database error",
                             f"The application cannot start.\n\n{exc}")
        root.destroy()
        return
    App(db).mainloop()


if __name__ == "__main__":
    main()
