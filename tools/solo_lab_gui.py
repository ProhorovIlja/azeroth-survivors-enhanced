"""Optional local Tkinter controller for the safe solo save lab.

Never performs an action without a real button click/confirmation. The tool is
not a game trainer and does not install or auto-run any third-party software.
"""
import json
import os
from pathlib import Path
import sys
import webbrowser

from tools import addon_audit, solo_lab


EDITORS = {
    "FlixxFlix (offline save editor, MIT)": "https://github.com/FlixxFlix/AzerothSurvivors-SaveEditor",
    "Shilen (local-in-browser save editor)": "https://yssadora.github.io/azeroth-survivors-editor/",
    "Legacy Godot Editor (tested 0.104, MIT)": "https://github.com/oppahansi/azssaveeditor",
}


def initial_paths(home=None, appdata=None):
    home = Path(home) if home else Path.home()
    appdata = appdata if appdata is not None else os.environ.get("APPDATA")
    return {
        "game_exe": "",
        "save_source": str(Path(appdata) / "wenilla-rogue" / "characters.txt") if appdata else "",
        "sandbox": str(home / "Documents" / "AZS-SoloLab-01"),
    }


def run():
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox, scrolledtext
    except ImportError as exc:
        raise RuntimeError("Tkinter is required for the optional GUI; use the CLI otherwise") from exc

    app = tk.Tk()
    app.title("Azeroth Survivors | Solo Cheat Lab")
    app.geometry("830x650")
    app.minsize(740, 540)
    app.configure(bg="#111822")
    paths = initial_paths()
    values = {key: tk.StringVar(value=value) for key, value in paths.items()}
    style = ttk.Style(app)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("TLabelframe", background="#111822", foreground="#e8c77a")
    style.configure("TLabelframe.Label", background="#111822", foreground="#e8c77a")
    style.configure("TLabel", background="#111822", foreground="#dde3e8")
    style.configure("TButton", padding=8)

    tk.Label(app, text="SOLO CHEAT LAB", font=("Segoe UI", 21, "bold"),
             bg="#111822", fg="#e8c77a").pack(anchor="w", padx=18, pady=(12, 3))
    tk.Label(app, text="Локальная копия сохранения • Проверка SHA-256 • Откат. Не God Mode и не изоляция сети.",
             font=("Segoe UI", 10), bg="#111822", fg="#bbc5cf").pack(anchor="w", padx=20, pady=(0, 12))

    section = ttk.LabelFrame(app, text="Файлы и песочница", padding=12)
    section.pack(fill="x", padx=18, pady=6)

    def choose_file(key, label):
        from tkinter import filedialog
        value = filedialog.askopenfilename(title=label)
        if value:
            values[key].set(value)

    for index, (key, caption, button) in enumerate([
        ("game_exe", "AzerothSurvivors.exe", "Выбрать EXE"),
        ("save_source", "Основной characters.txt", "Выбрать save"),
        ("sandbox", "НОВАЯ папка песочницы", "Родительская папка"),
    ]):
        ttk.Label(section, text=caption).grid(row=index, column=0, sticky="w", padx=(0, 10), pady=6)
        ttk.Entry(section, textvariable=values[key], width=72).grid(row=index, column=1, sticky="ew", pady=6)
        if key == "sandbox":
            def choose_parent():
                folder = filedialog.askdirectory(title="Куда поместить новую песочницу?")
                if folder:
                    values["sandbox"].set(str(Path(folder) / "AZS-SoloLab-01"))
            callback = choose_parent
        else:
            callback = lambda k=key,c=caption: choose_file(k,c)
        ttk.Button(section, text=button, command=callback).grid(row=index, column=2, padx=(10, 0))
    section.columnconfigure(1, weight=1)

    actions = ttk.LabelFrame(app, text="Действия (изменения только после подтверждения)", padding=12)
    actions.pack(fill="x", padx=18, pady=8)

    log = scrolledtext.ScrolledText(app, height=11, bg="#0b1017", fg="#d9e2eb", insertbackground="white",
                                   font=("Consolas", 10), wrap="word", relief="flat", state="disabled")
    log.pack(fill="both", expand=True, padx=18, pady=8)

    def show(data):
        log.configure(state="normal")
        log.insert("end", json.dumps(data, indent=2, ensure_ascii=False) + "\n\n")
        log.see("end")
        log.configure(state="disabled")

    def attempt(fn):
        try:
            show(fn())
        except (solo_lab.LabError, addon_audit.AuditError, OSError) as exc:
            messagebox.showerror("Операция не выполнена", str(exc))
            show({"status": "REFUSED", "reason": str(exc)})

    def ask(text):
        return messagebox.askyesno("Подтвердить Solo Cheat Lab", text)

    def inspect():
        attempt(lambda: solo_lab.inspect(values["game_exe"].get(), values["save_source"].get()))

    def prepare():
        if ask("Создать НОВУЮ песочницу и скопировать туда сохранение? Основное сохранение не изменяется."):
            attempt(lambda: solo_lab.prepare(values["game_exe"].get(), values["save_source"].get(),
                                             values["sandbox"].get(), True))

    def launch():
        if ask("Запустить игру с отдельным primary save? ДРУГИЕ настройки и сеть не изолированы. Используй одиночный режим."):
            attempt(lambda: solo_lab.launch(values["sandbox"].get(), True))

    def restore():
        if ask("Сбросить сохранение ТОЛЬКО в песочнице? Текущая версия будет предварительно сохранена."):
            attempt(lambda: solo_lab.restore(values["sandbox"].get(), True))

    def audit():
        exe = Path(values["game_exe"].get())
        attempt(lambda: addon_audit.scan(exe.parent))

    for col,(title,fn) in enumerate([
        ("Проверить", inspect), ("Создать песочницу", prepare),
        ("Состояние", lambda: attempt(lambda: solo_lab.status(values["sandbox"].get()))),
        ("Снимок", lambda: attempt(lambda: solo_lab.snapshot(values["sandbox"].get()))),
        ("Запустить игру", launch), ("Откат", restore), ("Проверить аддоны", audit),
    ]):
        row,col2=divmod(col,4)
        ttk.Button(actions, text=title, command=fn).grid(row=row, column=col2, sticky="ew", padx=3, pady=4)
    for i in range(4): actions.columnconfigure(i, weight=1)

    footer = ttk.Frame(app)
    footer.pack(fill="x", padx=18, pady=(0, 12))
    ttk.Label(footer,text="Редакторы сохранений (открыть страницу проекта, не запускать EXE): ").pack(side="left")
    opts = tk.StringVar(value=list(EDITORS)[0])
    cb = ttk.Combobox(footer, textvariable=opts, values=list(EDITORS), state="readonly", width=39)
    cb.pack(side="left", padx=6, fill="x", expand=True)
    ttk.Button(footer, text="Открыть GitHub", command=lambda: webbrowser.open(EDITORS[opts.get()])).pack(side="right")
    app.mainloop()


def main():
    try:
        run()
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
