#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Argent Media Converter 2.1
Conversor multimedia moderno · GTK4 + Libadwaita
Audio / Vídeo · lotes · filtros · encoders HW reales (NVENC, VAAPI, QSV)
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib, Gdk
import subprocess
import threading
import os
import sys
import shutil
import signal
import re

APP_ID  = "io.github.Tavo78ok.ArgentMediaConverter"
VERSION = "2.1.4"

# ── Formatos ──────────────────────────────────────────────────────────────────

AUDIO_FORMATS = {
    "MP3":  {"codec": "libmp3lame", "ext": "mp3",  "lossy": True},
    "AAC":  {"codec": "aac",        "ext": "aac",  "lossy": True},
    "M4A":  {"codec": "aac",        "ext": "m4a",  "lossy": True},
    "FLAC": {"codec": "flac",       "ext": "flac", "lossy": False},
    "OGG":  {"codec": "libvorbis",  "ext": "ogg",  "lossy": True},
    "OPUS": {"codec": "libopus",    "ext": "opus", "lossy": True},
    "WAV":  {"codec": "pcm_s16le",  "ext": "wav",  "lossy": False},
    "AIFF": {"codec": "pcm_s16be",  "ext": "aiff", "lossy": False},
    "WMA":  {"codec": "wmav2",      "ext": "wma",  "lossy": True},
    "AC3":  {"codec": "ac3",        "ext": "ac3",  "lossy": True},
}

# vcodec_sw = software; hw maps override when acceleration is selected
VIDEO_FORMATS = {
    "MP4 H.264":  {"vcodec": "libx264",    "acodec": "aac",     "ext": "mp4", "family": "h264"},
    "MP4 H.265":  {"vcodec": "libx265",    "acodec": "aac",     "ext": "mp4", "family": "hevc"},
    "MKV H.264":  {"vcodec": "libx264",    "acodec": "aac",     "ext": "mkv", "family": "h264"},
    "MKV H.265":  {"vcodec": "libx265",    "acodec": "aac",     "ext": "mkv", "family": "hevc"},
    "WebM VP9":   {"vcodec": "libvpx-vp9", "acodec": "libopus", "ext": "webm","family": "vp9"},
    "WebM VP8":   {"vcodec": "libvpx",     "acodec": "libvorbis","ext": "webm","family": "vp8"},
    "AVI":        {"vcodec": "mpeg4",      "acodec": "mp3",     "ext": "avi", "family": "mpeg4"},
    "MOV":        {"vcodec": "libx264",    "acodec": "aac",     "ext": "mov", "family": "h264"},
    "GIF":        {"vcodec": "gif",        "acodec": None,      "ext": "gif", "family": "gif"},
    "3GP":        {"vcodec": "libx264",    "acodec": "aac",     "ext": "3gp", "family": "h264"},
}

# Hardware encoder mapping: family → backend → encoder name
HW_ENCODERS = {
    "h264": {
        "nvenc": "h264_nvenc",
        "vaapi": "h264_vaapi",
        "qsv":   "h264_qsv",
    },
    "hevc": {
        "nvenc": "hevc_nvenc",
        "vaapi": "hevc_vaapi",
        "qsv":   "hevc_qsv",
    },
    "vp9": {
        "vaapi": "vp9_vaapi",
        "qsv":   "vp9_qsv",
    },
    "av1": {
        "nvenc": "av1_nvenc",
        "vaapi": "av1_vaapi",
        "qsv":   "av1_qsv",
    },
}

SAMPLE_RATES   = ["8000", "16000", "22050", "32000", "44100", "48000", "96000"]
AUDIO_BITRATES = ["64k", "96k", "128k", "160k", "192k", "224k", "256k", "320k"]
CHANNELS       = {"Mono": "1", "Estéreo": "2", "5.1": "6", "7.1": "8"}
RESOLUTIONS    = [
    "Original",
    "426x240", "640x360", "854x480", "1280x720",
    "1920x1080", "2560x1440", "3840x2160", "Personalizada"
]
FRAMERATES     = ["Original", "15", "24", "25", "30", "48", "60"]
PRESETS_SW     = ["ultrafast", "superfast", "veryfast", "faster", "fast",
                  "medium", "slow", "slower", "veryslow"]
PRESETS_NVENC  = ["p1", "p2", "p3", "p4", "p5", "p6", "p7"]  # p1=fastest … p7=best
HW_BACKENDS    = {
    "Sin aceleración (CPU)": "none",
    "NVENC (NVIDIA)":        "nvenc",
    "VAAPI (Intel/AMD)":     "vaapi",
    "QSV (Intel Quick Sync)":"qsv",
}

CSS = """
/* ── Base ─────────────────────────────────────────────────────────────────── */
window, .background {
    background-color: #1c2128;
    color: #e6edf3;
}
.sidebar {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}

/* ── Lista de formatos ────────────────────────────────────────────────────── */
.format-row {
    padding: 10px 12px;
    border-radius: 8px;
    margin: 2px 6px;
}
.format-row:selected {
    background-color: alpha(#58a6ff, 0.22);
}
.format-ext {
    font-family: 'JetBrains Mono','Fira Code',monospace;
    font-weight: 700;
    font-size: 13px;
    color: #79c0ff;
}
.format-name {
    font-size: 11px;
    color: #b1bac4;
}

/* ── Comando ──────────────────────────────────────────────────────────────── */
.cmd-view {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-left: 3px solid #58a6ff;
    border-radius: 8px;
    padding: 12px;
    font-family: 'JetBrains Mono','Fira Code',monospace;
    font-size: 12px;
    color: #7ee787;
}
textview {
    background-color: #0d1117;
    color: #7ee787;
}
textview text {
    background-color: #0d1117;
    color: #7ee787;
}

/* ── Etiquetas ────────────────────────────────────────────────────────────── */
.section {
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8b949e;
    font-weight: 700;
}
label { color: #e6edf3; }
.codec-badge {
    font-family: 'JetBrains Mono',monospace;
    font-size: 12px;
    font-weight: 600;
    color: #79c0ff;
    background-color: alpha(#58a6ff, 0.18);
    border: 1px solid alpha(#58a6ff, 0.4);
    border-radius: 6px;
    padding: 4px 10px;
}
.batch-label {
    font-size: 12px;
    color: #3fb950;
    font-family: 'JetBrains Mono',monospace;
}
.hw-badge {
    font-size: 11px;
    color: #e3b341;
    font-family: 'JetBrains Mono',monospace;
}
.title-accent { color: #58a6ff; font-weight: 800; }

/* ── Botones ──────────────────────────────────────────────────────────────── */
.mode-active {
    background-color: #58a6ff;
    color: #0d1117;
    font-weight: 700;
}
.run-btn {
    background-color: #238636;
    color: #ffffff;
    font-weight: 700;
    border-radius: 8px;
    padding: 8px 18px;
}
.run-btn:hover { background-color: #2ea043; }
.copy-btn {
    background-color: #30363d;
    color: #e6edf3;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 14px;
}
.copy-btn:hover { background-color: #484f58; }
.cancel-btn {
    background-color: #da3633;
    color: #ffffff;
    font-weight: 700;
    border-radius: 8px;
}
.pick-btn {
    background-color: #238636;
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px 16px;
}
.pick-btn:hover { background-color: #2ea043; }
.folder-btn {
    background-color: #30363d;
    color: #e6edf3;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 14px;
}
.folder-btn:hover { background-color: #484f58; }
.clear-btn {
    background-color: #21262d;
    color: #c9d1d9;
    font-weight: 600;
    border-radius: 8px;
    padding: 6px 12px;
    border: 1px solid #30363d;
}
.clear-btn:hover { background-color: #30363d; color: #e6edf3; }

/* ── Tarjeta de archivos ──────────────────────────────────────────────────── */
.file-card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 14px 16px;
}

/* ── Entries ──────────────────────────────────────────────────────────────── */
entry {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
    min-height: 36px;
    padding: 4px 10px;
    caret-color: #e6edf3;
}
entry:focus { border-color: #58a6ff; }
entry placeholder { color: #6e7681; }

/* ── Notebook (pestañas Básico/Calidad/Tiempo) — el problema del blanco ─── */
notebook {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
}
notebook > header {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
}
notebook > header > tabs > tab {
    background-color: transparent;
    color: #8b949e;
    padding: 8px 14px;
    border-radius: 8px 8px 0 0;
}
notebook > header > tabs > tab:checked {
    background-color: #21262d;
    color: #e6edf3;
    font-weight: 700;
}
notebook > stack {
    background-color: #161b22;
}
notebook > stack > * {
    background-color: #161b22;
    color: #e6edf3;
}

/* ── DropDown / combos ────────────────────────────────────────────────────── */
dropdown {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
    min-height: 36px;
}
dropdown > button {
    background-color: #0d1117;
    color: #e6edf3;
    border-radius: 8px;
}
dropdown > button:hover {
    background-color: #21262d;
}
/* Lista emergente del dropdown */
popover {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 8px;
}
popover listview,
popover listview > row {
    background-color: #161b22;
    color: #e6edf3;
}
popover listview > row:hover,
popover listview > row:selected {
    background-color: alpha(#58a6ff, 0.25);
}

/* ── Scales / switches ────────────────────────────────────────────────────── */
scale trough { background-color: #30363d; }
scale highlight { background-color: #58a6ff; }
switch { background-color: #30363d; }
switch:checked { background-color: #238636; }

/* ── Preferences / SwitchRow ──────────────────────────────────────────────── */
.preferences-group,
row {
    background-color: #161b22;
    color: #e6edf3;
}
row:hover { background-color: #21262d; }

/* ── Progress ─────────────────────────────────────────────────────────────── */
progressbar trough {
    background-color: #30363d;
    border-radius: 4px;
    min-height: 6px;
}
progressbar progress {
    background-color: #58a6ff;
    border-radius: 4px;
}

/* ── ScrolledWindow ───────────────────────────────────────────────────────── */
scrolledwindow { background-color: transparent; }
scrolledwindow > viewport { background-color: transparent; }
"""

# ── Utilidades ────────────────────────────────────────────────────────────────

def parse_time(tstr):
    if not tstr or not str(tstr).strip():
        return None
    tstr = str(tstr).strip()
    try:
        if ":" in tstr:
            parts = [float(x) for x in tstr.split(":")]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
        return float(tstr)
    except ValueError:
        return None


def probe_duration(path):
    if not path or not os.path.isfile(path):
        return None
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            text=True, stderr=subprocess.DEVNULL, timeout=6)
        return float(out.strip())
    except Exception:
        return None


def safe_idx(combo, items, default=0):
    try:
        idx = combo.get_selected()
        if idx is None or idx < 0 or idx >= len(items):
            return default
        return idx
    except Exception:
        return default


def detect_hw_encoders():
    """Detecta qué backends HW están disponibles en este sistema."""
    available = {"none"}
    try:
        out = subprocess.check_output(
            ["ffmpeg", "-hide_banner", "-encoders"],
            text=True, stderr=subprocess.DEVNULL, timeout=5)
        if "h264_nvenc" in out or "hevc_nvenc" in out:
            available.add("nvenc")
        if "h264_vaapi" in out or "hevc_vaapi" in out:
            available.add("vaapi")
        if "h264_qsv" in out or "hevc_qsv" in out:
            available.add("qsv")
    except Exception:
        pass
    return available


def find_vaapi_device():
    """Busca un render node VAAPI usable."""
    for path in ("/dev/dri/renderD128", "/dev/dri/renderD129", "/dev/dri/card0"):
        if os.path.exists(path):
            return path
    return "/dev/dri/renderD128"


# ── Ventana principal ─────────────────────────────────────────────────────────

class ConverterWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Argent Media Converter")
        self.set_default_size(1120, 780)
        self.set_size_request(920, 640)

        self.mode = "audio"
        self.selected_format = "MP3"
        self.fmt_keys = []
        self.batch_queue = []
        self.process = None
        self._cancel_requested = False
        self._log_queue = []          # buffer para no saturar la UI
        self._log_flush_id = None
        self.ui_ready = False
        self._setting_batch = False
        self.hw_available = detect_hw_encoders()

        # Refuerzo de tema oscuro por ventana
        try:
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception:
            pass

        self._apply_css()
        self._build_ui()
        self._populate_formats()
        self._populate_combo()
        self.ui_ready = True
        self._update_visibility()
        self._update_command()

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        t1 = Gtk.Label(label="ARGENT")
        t1.add_css_class("title-3")
        t2 = Gtk.Label(label=" MEDIA")
        t2.add_css_class("title-3")
        t2.add_css_class("title-accent")
        t3 = Gtk.Label(label=" CONVERTER")
        t3.add_css_class("title-3")
        title_box.append(t1)
        title_box.append(t2)
        title_box.append(t3)
        header.set_title_widget(title_box)

        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        mode_box.add_css_class("linked")
        self.btn_audio = Gtk.Button(label="Audio")
        self.btn_audio.add_css_class("mode-active")
        self.btn_audio.connect("clicked", lambda *_: self._set_mode("audio"))
        self.btn_video = Gtk.Button(label="Vídeo")
        self.btn_video.connect("clicked", lambda *_: self._set_mode("video"))
        mode_box.append(self.btn_audio)
        mode_box.append(self.btn_video)
        header.pack_start(mode_box)

        about_btn = Gtk.Button(icon_name="help-about-symbolic")
        about_btn.connect("clicked", self._show_about)
        header.pack_end(about_btn)

        self.toast = Adw.ToastOverlay()

        split = Adw.OverlaySplitView()
        split.set_sidebar_width_fraction(0.19)
        split.set_collapsed(False)

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.add_css_class("sidebar")
        sidebar.set_size_request(190, -1)
        side_lbl = Gtk.Label(label="FORMATO")
        side_lbl.add_css_class("section")
        side_lbl.set_halign(Gtk.Align.START)
        side_lbl.set_margin_start(14)
        side_lbl.set_margin_top(16)
        side_lbl.set_margin_bottom(8)
        sidebar.append(side_lbl)
        scroll_side = Gtk.ScrolledWindow()
        scroll_side.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_side.set_vexpand(True)
        self.fmt_list = Gtk.ListBox()
        self.fmt_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.fmt_list.add_css_class("navigation-sidebar")
        self.fmt_list.connect("row-selected", self._on_format_row)
        scroll_side.set_child(self.fmt_list)
        sidebar.append(scroll_side)
        split.set_sidebar(sidebar)

        # Main
        main_scroll = Gtk.ScrolledWindow()
        main_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_scroll.set_vexpand(True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_margin_start(28)
        content.set_margin_end(28)
        content.set_margin_top(20)
        content.set_margin_bottom(20)

        content.append(self._build_files())
        content.append(self._sep())
        content.append(self._build_format_row())
        content.append(self._sep())

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.notebook.set_margin_top(4)
        self.notebook.append_page(self._page_basic(), self._tab("Básico"))
        self.notebook.append_page(self._page_quality(), self._tab("Calidad"))
        self.notebook.append_page(self._page_timing(), self._tab("Tiempo"))
        self.notebook.connect("switch-page", lambda *_: self._update_command())
        content.append(self.notebook)
        content.append(self._sep())

        cmd_lbl = Gtk.Label(label="COMANDO")
        cmd_lbl.add_css_class("section")
        cmd_lbl.set_halign(Gtk.Align.START)
        cmd_lbl.set_margin_top(8)
        cmd_lbl.set_margin_bottom(6)
        content.append(cmd_lbl)

        self.cmd_view = Gtk.TextView()
        self.cmd_view.set_editable(False)
        self.cmd_view.set_cursor_visible(False)
        self.cmd_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.cmd_view.add_css_class("cmd-view")
        self.cmd_buffer = self.cmd_view.get_buffer()
        content.append(self.cmd_view)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_row.set_margin_top(14)
        btn_row.set_halign(Gtk.Align.END)
        self.copy_btn = Gtk.Button(label="Copiar")
        self.copy_btn.add_css_class("copy-btn")
        self.copy_btn.connect("clicked", self._copy_cmd)
        self.cancel_btn = Gtk.Button(label="⏹  Terminar")
        self.cancel_btn.add_css_class("cancel-btn")
        self.cancel_btn.set_visible(False)
        self.cancel_btn.set_tooltip_text("Detiene la conversión en curso")
        self.cancel_btn.connect("clicked", self._cancel)
        self.run_btn = Gtk.Button(label="▶  Convertir")
        self.run_btn.add_css_class("run-btn")
        self.run_btn.connect("clicked", self._run)
        btn_row.append(self.copy_btn)
        btn_row.append(self.cancel_btn)
        btn_row.append(self.run_btn)
        content.append(btn_row)

        self.progress = Gtk.ProgressBar()
        self.progress.set_margin_top(12)
        self.progress.set_visible(False)
        content.append(self.progress)

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        log_scroll.set_size_request(-1, 130)
        log_scroll.set_margin_top(8)
        log_scroll.set_visible(False)
        self.log_scroll = log_scroll
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.add_css_class("cmd-view")
        self.log_buffer = self.log_view.get_buffer()
        log_scroll.set_child(self.log_view)
        content.append(log_scroll)

        main_scroll.set_child(content)
        split.set_content(main_scroll)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(split)
        self.toast.set_child(toolbar)
        self.set_content(self.toast)

    def _sep(self):
        s = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        s.set_margin_top(14)
        s.set_margin_bottom(6)
        return s

    def _tab(self, text):
        lbl = Gtk.Label(label=text)
        lbl.set_margin_start(8)
        lbl.set_margin_end(8)
        return lbl

    def _combo(self, label, items, default=0, cb=None):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl = Gtk.Label(label=label)
        lbl.add_css_class("section")
        lbl.set_halign(Gtk.Align.START)
        combo = Gtk.DropDown.new_from_strings(items)
        combo.set_hexpand(True)
        combo.set_selected(min(default, max(0, len(items) - 1)))
        combo.connect("notify::selected",
                      lambda *_: (cb() if cb else self._update_command()))
        box.append(lbl)
        box.append(combo)
        return box, combo

    def _entry(self, label, placeholder=""):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl = Gtk.Label(label=label)
        lbl.add_css_class("section")
        lbl.set_halign(Gtk.Align.START)
        entry = Gtk.Entry()
        entry.set_placeholder_text(placeholder)
        entry.connect("changed", lambda *_: self._update_command())
        box.append(lbl)
        box.append(entry)
        return box, entry

    def _scale(self, label, lo, hi, step, digits, default):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label=label)
        lbl.add_css_class("section")
        lbl.set_halign(Gtk.Align.START)
        val_lbl = Gtk.Label(label=f"{default:.{digits}f}")
        val_lbl.set_halign(Gtk.Align.END)
        val_lbl.set_hexpand(True)
        top.append(lbl)
        top.append(val_lbl)
        adj = Gtk.Adjustment(value=default, lower=lo, upper=hi, step_increment=step)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_digits(digits)
        scale.set_hexpand(True)
        scale.connect("value-changed", lambda s: (
            val_lbl.set_label(f"{s.get_value():.{digits}f}"),
            self._update_command()))
        box.append(top)
        box.append(scale)
        return box, scale

    def _switch(self, title, subtitle=""):
        row = Adw.SwitchRow()
        row.set_title(title)
        if subtitle:
            row.set_subtitle(subtitle)
        row.connect("notify::active", lambda *_: self._update_command())
        return row

    def _build_files(self):
        # Tarjeta visible con botones grandes y claros
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("file-card")

        # ── Entrada ──────────────────────────────────────────────────────────
        in_lbl = Gtk.Label(label="1.  ARCHIVO DE ENTRADA")
        in_lbl.add_css_class("section")
        in_lbl.set_halign(Gtk.Align.START)
        card.append(in_lbl)

        in_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.input_entry = Gtk.Entry()
        self.input_entry.set_placeholder_text("Haz clic en «Elegir archivo…» o escribe la ruta")
        self.input_entry.set_hexpand(True)
        self.input_entry.connect("changed", self._on_input_changed)

        pick = Gtk.Button(label="📂  Elegir archivo…")
        pick.add_css_class("pick-btn")
        pick.set_tooltip_text("Abre el selector. Ctrl+clic para varios archivos (lote)")
        pick.connect("clicked", self._pick_input)

        in_row.append(self.input_entry)
        in_row.append(pick)
        card.append(in_row)

        self.batch_lbl = Gtk.Label(label="")
        self.batch_lbl.add_css_class("batch-label")
        self.batch_lbl.set_halign(Gtk.Align.START)
        self.batch_lbl.set_visible(False)
        card.append(self.batch_lbl)

        # Separador visual
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        card.append(sep)

        # ── Salida ───────────────────────────────────────────────────────────
        out_lbl = Gtk.Label(label="2.  NOMBRE / CARPETA DE SALIDA")
        out_lbl.add_css_class("section")
        out_lbl.set_halign(Gtk.Align.START)
        card.append(out_lbl)

        out_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.output_entry = Gtk.Entry()
        self.output_entry.set_placeholder_text("Se rellena solo al elegir el archivo (puedes cambiarlo)")
        self.output_entry.set_hexpand(True)
        self.output_entry.connect("changed", lambda *_: self._update_command())

        folder = Gtk.Button(label="📁  Carpeta…")
        folder.add_css_class("folder-btn")
        folder.set_tooltip_text("Elegir carpeta de salida")
        folder.connect("clicked", self._pick_output_dir)

        out_row.append(self.output_entry)
        out_row.append(folder)
        card.append(out_row)

        # Fila inferior: tip + limpiar
        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom.set_margin_top(4)
        tip = Gtk.Label()
        tip.set_markup(
            '<span size="small" foreground="#8b949e">'
            'Flujo:  Elegir archivo  →  formato (izquierda)  →  Convertir'
            '</span>')
        tip.set_halign(Gtk.Align.START)
        tip.set_hexpand(True)
        clear_btn = Gtk.Button(label="🗑  Limpiar")
        clear_btn.add_css_class("clear-btn")
        clear_btn.set_tooltip_text(
            "Vacía entrada, salida, lote y log (después de convertir)")
        clear_btn.connect("clicked", self._clear_files)
        bottom.append(tip)
        bottom.append(clear_btn)
        card.append(bottom)

        return card

    def _build_format_row(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        row.set_margin_top(4)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        left.set_hexpand(True)
        lbl = Gtk.Label(label="FORMATO DE SALIDA")
        lbl.add_css_class("section")
        lbl.set_halign(Gtk.Align.START)
        self.fmt_combo = Gtk.DropDown()
        self.fmt_combo.set_hexpand(True)
        self.fmt_combo.connect("notify::selected", lambda *_: self._on_combo_format())
        left.append(lbl)
        left.append(self.fmt_combo)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl2 = Gtk.Label(label="CODEC / ENCODER")
        lbl2.add_css_class("section")
        lbl2.set_halign(Gtk.Align.START)
        self.codec_lbl = Gtk.Label(label="—")
        self.codec_lbl.add_css_class("codec-badge")
        self.codec_lbl.set_halign(Gtk.Align.START)
        right.append(lbl2)
        right.append(self.codec_lbl)
        self.hw_info = Gtk.Label(label="")
        self.hw_info.add_css_class("hw-badge")
        self.hw_info.set_halign(Gtk.Align.START)
        right.append(self.hw_info)
        row.append(left)
        row.append(right)
        return row

    def _page_basic(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(16)
        box.set_margin_bottom(12)
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(14)
        grid.set_column_homogeneous(True)

        sr_box, self.sr_combo = self._combo(
            "TASA DE MUESTREO", [f"{r} Hz" for r in SAMPLE_RATES], 5)
        ch_box, self.ch_combo = self._combo("CANALES", list(CHANNELS.keys()), 1)
        br_box, self.abr_combo = self._combo("BITRATE AUDIO", AUDIO_BITRATES, 4)
        fps_box, self.fps_combo = self._combo("FRAMERATE", FRAMERATES, 0)
        self.fps_box = fps_box
        fps_box.set_visible(False)

        grid.attach(sr_box, 0, 0, 1, 1)
        grid.attach(ch_box, 1, 0, 1, 1)
        grid.attach(br_box, 0, 1, 1, 1)
        grid.attach(fps_box, 1, 1, 1, 1)
        box.append(grid)

        self.res_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.res_outer.set_visible(False)
        res_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        rb, self.res_combo = self._combo("RESOLUCIÓN", RESOLUTIONS, 0,
                                         cb=self._on_res_changed)
        rb.set_hexpand(True)
        cb, self.custom_res = self._entry("PERSONALIZADA", "1920x1080")
        cb.set_hexpand(True)
        cb.set_visible(False)
        self.custom_res_box = cb
        res_row.append(rb)
        res_row.append(cb)
        self.res_outer.append(res_row)
        self.keep_ar = self._switch(
            "Mantener relación de aspecto",
            "Evita distorsión al redimensionar (recomendado)")
        self.keep_ar.set_active(True)
        self.res_outer.append(self.keep_ar)
        box.append(self.res_outer)
        return box

    def _page_quality(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(16)
        box.set_margin_bottom(12)

        vol_box, self.vol_scale = self._scale(
            "VOLUMEN  (1.0 = original)", 0.1, 4.0, 0.05, 2, 1.0)
        crf_box, self.crf_scale = self._scale(
            "CALIDAD  (CRF/CQ/QP · 0=mejor · 23=default · 51=peor)", 0, 51, 1, 0, 23)
        self.crf_box = crf_box

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(14)
        grid.set_column_homogeneous(True)

        # Preset labels adapt to HW later; start with software list
        pre_box, self.pre_combo = self._combo("PRESET", PRESETS_SW, 5)
        self.pre_box = pre_box

        # Solo mostrar backends disponibles
        hw_labels = []
        for label, key in HW_BACKENDS.items():
            if key == "none" or key in self.hw_available:
                hw_labels.append(label)
        if not hw_labels:
            hw_labels = list(HW_BACKENDS.keys())
        self._hw_labels = hw_labels
        self._hw_keys = [HW_BACKENDS[l] for l in hw_labels]

        hw_box, self.hw_combo = self._combo(
            "ENCODER HARDWARE", hw_labels, 0, cb=self._on_hw_changed)
        self.hw_box = hw_box

        grid.attach(vol_box, 0, 0, 2, 1)
        grid.attach(crf_box, 0, 1, 2, 1)
        grid.attach(pre_box, 0, 2, 1, 1)
        grid.attach(hw_box, 1, 2, 1, 1)
        box.append(grid)

        self.norm_row = self._switch(
            "Normalización EBU R128 (loudnorm)",
            "Loudness a −23 LUFS — estándar broadcast")
        self.strip_row = self._switch(
            "Eliminar audio (−an)",
            "Exportar solo la pista de vídeo")
        self.twopass_row = self._switch(
            "Codificación en 2 pasadas (solo CPU)",
            "Mejor distribución de bitrate — no aplica a HW")

        group = Adw.PreferencesGroup()
        group.set_margin_top(8)
        group.add(self.norm_row)
        group.add(self.strip_row)
        group.add(self.twopass_row)
        box.append(group)
        return box

    def _page_timing(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(16)
        box.set_margin_bottom(12)
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(14)
        grid.set_column_homogeneous(True)
        sb, self.start_entry = self._entry("INICIO", "00:01:30  o  90")
        db, self.dur_entry = self._entry("DURACIÓN", "00:00:30  o  30")
        fb, self.fi_entry = self._entry("FADE IN (seg)", "2")
        ob, self.fo_entry = self._entry("FADE OUT (seg)", "3")
        grid.attach(sb, 0, 0, 1, 1)
        grid.attach(db, 1, 0, 1, 1)
        grid.attach(fb, 0, 1, 1, 1)
        grid.attach(ob, 1, 1, 1, 1)
        box.append(grid)
        tip = Gtk.Label()
        tip.set_markup(
            '<span size="small" foreground="#484f58">'
            '−ss antes del input = seek rápido por keyframe.\n'
            'Fade In/Out se aplican a la pista de audio (también en modo vídeo).\n'
            'Fade Out requiere poder leer la duración del archivo de entrada.\n'
            'Encoders HW: NVENC (NVIDIA), VAAPI (Intel/AMD), QSV (Intel).'
            '</span>')
        tip.set_halign(Gtk.Align.START)
        tip.set_wrap(True)
        tip.set_margin_top(6)
        box.append(tip)
        return box

    # ── Formatos / modo ───────────────────────────────────────────────────────

    def _populate_formats(self):
        while True:
            child = self.fmt_list.get_first_child()
            if not child:
                break
            self.fmt_list.remove(child)
        fmts = AUDIO_FORMATS if self.mode == "audio" else VIDEO_FORMATS
        first = None
        for name, info in fmts.items():
            row = Gtk.ListBoxRow()
            row.set_name(name)
            row.add_css_class("format-row")
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            vbox.set_margin_start(4)
            vbox.set_margin_end(4)
            vbox.set_margin_top(2)
            vbox.set_margin_bottom(2)
            l1 = Gtk.Label(label=f".{info['ext']}")
            l1.add_css_class("format-ext")
            l1.set_halign(Gtk.Align.START)
            l2 = Gtk.Label(label=name)
            l2.add_css_class("format-name")
            l2.set_halign(Gtk.Align.START)
            vbox.append(l1)
            vbox.append(l2)
            row.set_child(vbox)
            self.fmt_list.append(row)
            if first is None:
                first = row
        if first:
            self.fmt_list.select_row(first)

    def _populate_combo(self):
        fmts = AUDIO_FORMATS if self.mode == "audio" else VIDEO_FORMATS
        self.fmt_keys = list(fmts.keys())
        model = Gtk.StringList()
        for name in self.fmt_keys:
            model.append(f".{fmts[name]['ext']}  —  {name}")
        self.fmt_combo.set_model(model)
        self.fmt_combo.set_selected(0)
        self.selected_format = self.fmt_keys[0]
        self._update_codec()

    def _on_format_row(self, listbox, row):
        if not row or not self.ui_ready:
            return
        self.selected_format = row.get_name()
        if self.fmt_keys and self.selected_format in self.fmt_keys:
            self.fmt_combo.set_selected(self.fmt_keys.index(self.selected_format))
        self._update_codec()
        self._update_visibility()
        self._update_command()

    def _on_combo_format(self):
        if not self.ui_ready:
            return
        idx = safe_idx(self.fmt_combo, self.fmt_keys, 0)
        if not self.fmt_keys:
            return
        self.selected_format = self.fmt_keys[idx]
        row = self.fmt_list.get_row_at_index(idx)
        if row:
            self.fmt_list.select_row(row)
        self._update_codec()
        self._update_visibility()
        self._update_command()

    def _on_hw_changed(self):
        if not self.ui_ready:
            return
        backend = self._current_hw()
        # Cambiar lista de presets según backend
        if backend == "nvenc":
            items = PRESETS_NVENC
            default = 3  # p4
        else:
            items = PRESETS_SW
            default = 5  # medium
        model = Gtk.StringList()
        for p in items:
            model.append(p)
        self.pre_combo.set_model(model)
        self.pre_combo.set_selected(min(default, len(items) - 1))
        self._update_codec()
        self._update_command()

    def _current_hw(self):
        idx = safe_idx(self.hw_combo, self._hw_keys, 0)
        return self._hw_keys[idx]

    def _resolve_vcodec(self, fmt_info, backend):
        """Devuelve (encoder_name, is_hw)."""
        family = fmt_info.get("family", "")
        if backend == "none" or family not in HW_ENCODERS:
            return fmt_info["vcodec"], False
        mapping = HW_ENCODERS[family]
        if backend in mapping:
            return mapping[backend], True
        return fmt_info["vcodec"], False

    def _update_codec(self):
        fmts = AUDIO_FORMATS if self.mode == "audio" else VIDEO_FORMATS
        info = fmts.get(self.selected_format, {})
        if self.mode == "audio":
            codec = info.get("codec", "—")
            tag = "lossy" if info.get("lossy", True) else "lossless"
            self.codec_lbl.set_label(f"{codec}  ·  {tag}")
            self.hw_info.set_label("")
        else:
            backend = self._current_hw()
            vcodec, is_hw = self._resolve_vcodec(info, backend)
            acodec = info.get("acodec") or "—"
            self.codec_lbl.set_label(f"v:{vcodec}  /  a:{acodec}")
            if is_hw:
                self.hw_info.set_label(f"⚡ encoder hardware · {backend.upper()}")
            else:
                if backend != "none" and info.get("family") not in HW_ENCODERS:
                    self.hw_info.set_label("HW no disponible para este formato → CPU")
                else:
                    self.hw_info.set_label("")

    def _set_mode(self, mode):
        self.mode = mode
        self.selected_format = "MP3" if mode == "audio" else "MP4 H.264"
        if mode == "audio":
            self.btn_audio.add_css_class("mode-active")
            self.btn_video.remove_css_class("mode-active")
        else:
            self.btn_video.add_css_class("mode-active")
            self.btn_audio.remove_css_class("mode-active")
        self._populate_formats()
        self._populate_combo()
        self._update_visibility()
        self._update_command()

    def _on_res_changed(self):
        if not self.ui_ready:
            return
        sel = RESOLUTIONS[safe_idx(self.res_combo, RESOLUTIONS, 0)]
        self.custom_res_box.set_visible(sel == "Personalizada")
        self._update_command()

    def _update_visibility(self):
        if not self.ui_ready:
            return
        v = self.mode == "video"
        self.fps_box.set_visible(v)
        self.res_outer.set_visible(v)
        self.crf_box.set_visible(v)
        self.pre_box.set_visible(v)
        self.hw_box.set_visible(v)
        self.strip_row.set_visible(v)
        self.twopass_row.set_visible(v)

    # ── Comando ───────────────────────────────────────────────────────────────

    def _audio_filters(self, path, vol, norm, fi, fo, start, dur):
        af = []
        if abs(vol - 1.0) > 0.001:
            af.append(f"volume={vol}")
        if norm:
            af.append("loudnorm")
        d_fi = parse_time(fi)
        if d_fi and d_fi > 0:
            af.append(f"afade=t=in:st=0:d={d_fi}")
        d_fo = parse_time(fo)
        if d_fo and d_fo > 0:
            media = probe_duration(path)
            if media is not None:
                ss = parse_time(start) or 0.0
                effective = media - ss
                td = parse_time(dur)
                if td is not None:
                    effective = min(effective, td)
                if effective > d_fo:
                    st = max(0.0, effective - d_fo)
                    af.append(f"afade=t=out:st={st:.3f}:d={d_fo}")
        return af

    def _build_command(self, inp=None, outp=None):
        if not self.ui_ready:
            return ""
        inp = inp or self.input_entry.get_text().strip() or "entrada"
        outp = outp or self.output_entry.get_text().strip() or "output"
        start = self.start_entry.get_text().strip()
        dur = self.dur_entry.get_text().strip()
        vol = round(self.vol_scale.get_value(), 2)
        fi = self.fi_entry.get_text().strip()
        fo = self.fo_entry.get_text().strip()
        norm = self.norm_row.get_active()
        sr = SAMPLE_RATES[safe_idx(self.sr_combo, SAMPLE_RATES, 5)]
        ch = list(CHANNELS.values())[safe_idx(self.ch_combo, list(CHANNELS.keys()), 1)]
        abr = AUDIO_BITRATES[safe_idx(self.abr_combo, AUDIO_BITRATES, 4)]

        if self.mode == "audio":
            fmt = AUDIO_FORMATS.get(self.selected_format, list(AUDIO_FORMATS.values())[0])
            parts = ["ffmpeg", "-hide_banner", "-y"]
            if start:
                parts += ["-ss", start]
            parts += ["-i", f'"{inp}"']
            if dur:
                parts += ["-t", dur]
            parts += ["-c:a", fmt["codec"]]
            if fmt.get("lossy", True):
                parts += ["-b:a", abr]
            parts += ["-ar", sr, "-ac", ch]
            af = self._audio_filters(inp, vol, norm, fi, fo, start, dur)
            if af:
                parts += ["-af", f'"{",".join(af)}"']
            parts += [f'"{outp}.{fmt["ext"]}"']
            return " ".join(parts)

        # ── Vídeo ────────────────────────────────────────────────────────────
        fmt = VIDEO_FORMATS.get(self.selected_format, list(VIDEO_FORMATS.values())[0])
        backend = self._current_hw()
        vcodec, is_hw = self._resolve_vcodec(fmt, backend)
        acodec = fmt["acodec"]
        ext = fmt["ext"]
        family = fmt.get("family", "")

        fps = FRAMERATES[safe_idx(self.fps_combo, FRAMERATES, 0)]
        res = RESOLUTIONS[safe_idx(self.res_combo, RESOLUTIONS, 0)]
        if res == "Personalizada":
            res = self.custom_res.get_text().strip() or "1920x1080"
        quality = int(self.crf_scale.get_value())
        keep_ar = self.keep_ar.get_active()
        no_audio = self.strip_row.get_active()
        two_pass = self.twopass_row.get_active() and not is_hw

        # Preset actual
        if backend == "nvenc" and is_hw:
            preset_list = PRESETS_NVENC
            preset = preset_list[safe_idx(self.pre_combo, preset_list, 3)]
        else:
            preset = PRESETS_SW[safe_idx(self.pre_combo, PRESETS_SW, 5)]

        # GIF
        if ext == "gif":
            parts = ["ffmpeg", "-hide_banner", "-y"]
            if start:
                parts += ["-ss", start]
            parts += ["-i", f'"{inp}"']
            if dur:
                parts += ["-t", dur]
            try:
                gif_fps = float(fps) if fps != "Original" and float(fps) <= 30 else 15
            except ValueError:
                gif_fps = 15
            scale = res if res != "Original" else "iw:ih"
            vf = (f"fps={gif_fps},scale={scale}:flags=lanczos,"
                  "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse")
            parts += ["-vf", f'"{vf}"', "-loop", "0", f'"{outp}.gif"']
            return " ".join(parts)

        parts = ["ffmpeg", "-hide_banner", "-y"]

        # ── HW init ──────────────────────────────────────────────────────────
        if is_hw and backend == "nvenc":
            parts += ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        elif is_hw and backend == "vaapi":
            device = find_vaapi_device()
            parts += ["-vaapi_device", device,
                      "-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi"]
        elif is_hw and backend == "qsv":
            parts += ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"]

        if start:
            parts += ["-ss", start]
        parts += ["-i", f'"{inp}"']
        if dur:
            parts += ["-t", dur]

        # ── Video filters ────────────────────────────────────────────────────
        vf_parts = []
        if is_hw and backend == "vaapi":
            # VAAPI necesita hwupload si hay scale en software, o scale_vaapi
            if res != "Original":
                w, h = (res.split("x") + ["-2"])[:2] if "x" in res else (res, "-2")
                if keep_ar:
                    vf_parts.append(f"scale_vaapi=w={w}:h={h}:force_original_aspect_ratio=decrease")
                else:
                    vf_parts.append(f"scale_vaapi=w={w}:h={h}")
            else:
                vf_parts.append("scale_vaapi=format=nv12")
        elif is_hw and backend == "nvenc":
            # Con cuda frames, scale_cuda si es necesario
            if res != "Original":
                w, h = (res.split("x") + ["-2"])[:2] if "x" in res else (res, "-2")
                if keep_ar:
                    vf_parts.append(f"scale_cuda={w}:{h}:force_original_aspect_ratio=decrease")
                else:
                    vf_parts.append(f"scale_cuda={w}:{h}")
        elif is_hw and backend == "qsv":
            if res != "Original":
                w, h = (res.split("x") + ["-2"])[:2] if "x" in res else (res, "-2")
                vf_parts.append(f"scale_qsv={w}:{h}")
        else:
            # Software
            if res != "Original":
                if keep_ar and "x" in res:
                    w, h = res.split("x")
                    vf_parts.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease")
                    vf_parts.append(f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
                else:
                    vf_parts.append(f"scale={res}")

        if vf_parts:
            parts += ["-vf", f'"{",".join(vf_parts)}"']

        # ── Encoder + calidad ────────────────────────────────────────────────
        parts += ["-c:v", vcodec]

        if is_hw and backend == "nvenc":
            # NVENC: -cq (constant quality) 0-51, -preset p1..p7
            parts += ["-cq", str(quality), "-preset", preset, "-rc", "vbr"]
        elif is_hw and backend == "vaapi":
            # VAAPI: -qp 0-52
            parts += ["-qp", str(quality), "-rc_mode", "CQP"]
        elif is_hw and backend == "qsv":
            parts += ["-global_quality", str(quality)]
        else:
            # Software libx264/libx265/libvpx
            if vcodec in ("libx264", "libx265", "libvpx-vp9"):
                parts += ["-crf", str(quality)]
                if vcodec != "libvpx-vp9":
                    parts += ["-preset", preset]
            else:
                parts += ["-b:v", "4000k"]

        if fps != "Original":
            parts += ["-r", fps]

        # Audio
        if no_audio or not acodec:
            parts += ["-an"]
        else:
            parts += ["-c:a", acodec, "-b:a", abr, "-ar", sr]
            af = self._audio_filters(inp, vol, norm, fi, fo, start, dur)
            if af:
                parts += ["-af", f'"{",".join(af)}"']

        if two_pass:
            cleaned = []
            skip = False
            for p in parts:
                if skip:
                    skip = False
                    continue
                if p in ("-c:a", "-b:a", "-ar", "-af"):
                    skip = True
                    continue
                cleaned.append(p)
            p1 = " ".join(cleaned) + " -an -pass 1 -f null /dev/null"
            p2 = " ".join(parts) + f' -pass 2 "{outp}.{ext}"'
            return f"# Paso 1\n{p1}\n\n# Paso 2\n{p2}"

        parts.append(f'"{outp}.{ext}"')
        return " ".join(parts)

    def _update_command(self):
        if not self.ui_ready:
            return
        self.cmd_buffer.set_text(self._build_command())

    # ── Archivos ──────────────────────────────────────────────────────────────

    def _on_input_changed(self, *_):
        if self._setting_batch:
            self._update_command()
            return
        if self.batch_queue:
            self.batch_queue = []
            self.batch_lbl.set_visible(False)
        self._update_command()

    def _pick_input(self, *_):
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar archivo(s)")
        dialog.open_multiple(self, None, self._on_input_picked)

    def _on_input_picked(self, dialog, result):
        try:
            files = dialog.open_multiple_finish(result)
            if not files:
                return
            n = files.get_n_items()
            if n == 1:
                path = files.get_item(0).get_path()
                self.batch_queue = []
                self.input_entry.set_text(path)
                self.batch_lbl.set_visible(False)
                base = os.path.splitext(os.path.basename(path))[0]
                self.output_entry.set_text(
                    os.path.join(os.path.dirname(path), base + "_converted"))
            else:
                self.batch_queue = [files.get_item(i).get_path() for i in range(n)]
                self._setting_batch = True
                self.input_entry.set_text(f"{n} archivos seleccionados")
                self._setting_batch = False
                names = ", ".join(os.path.basename(p) for p in self.batch_queue[:3])
                extra = f" … +{n - 3}" if n > 3 else ""
                self.batch_lbl.set_label(f"Lote: {names}{extra}")
                self.batch_lbl.set_visible(True)
                self.output_entry.set_text(os.path.dirname(self.batch_queue[0]))
                self._update_command()
        except GLib.Error:
            pass

    def _pick_output_dir(self, *_):
        dialog = Gtk.FileDialog()
        dialog.set_title("Carpeta de salida")
        dialog.select_folder(self, None, self._on_output_dir)

    def _on_output_dir(self, dialog, result):
        try:
            f = dialog.select_folder_finish(result)
            if f:
                cur = self.output_entry.get_text()
                name = os.path.basename(cur) if cur else "output"
                self.output_entry.set_text(os.path.join(f.get_path(), name))
        except GLib.Error:
            pass

    # ── Limpiar / Ejecución ───────────────────────────────────────────────────

    def _clear_files(self, *_):
        """Vacía entrada, salida, lote y log para empezar de cero."""
        if not self.run_btn.get_sensitive():
            self._toast("Terminá o cancelá la conversión antes de limpiar")
            return
        self._setting_batch = True
        self.batch_queue = []
        self.input_entry.set_text("")
        self.output_entry.set_text("")
        self.batch_lbl.set_label("")
        self.batch_lbl.set_visible(False)
        self._setting_batch = False
        self.log_buffer.set_text("")
        self.log_scroll.set_visible(False)
        self.progress.set_visible(False)
        self._update_command()
        self._toast("🗑 Listo para un archivo nuevo")

    def _copy_cmd(self, *_):
        start, end = self.cmd_buffer.get_bounds()
        text = self.cmd_buffer.get_text(start, end, False)
        Gdk.Display.get_default().get_clipboard().set(text)
        self.copy_btn.set_label("✓ Copiado")
        GLib.timeout_add(1800, lambda: self.copy_btn.set_label("Copiar") or False)

    def _kill_process(self):
        """Mata el proceso ffmpeg (y su grupo) de forma agresiva."""
        proc = self.process
        if not proc or proc.poll() is not None:
            return
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        # Si no muere en ~1.5 s, SIGKILL
        def _force():
            if proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            return False
        GLib.timeout_add(1500, _force)

    def _cancel(self, *_):
        self._cancel_requested = True
        self._kill_process()
        self._append_log("\n── ⏹ Terminado por el usuario ──\n")
        self._toast("⏹ Proceso terminado")
        # UI se restaura; el worker saldrá al ver la bandera / proceso muerto
        self.run_btn.set_sensitive(True)
        self.cancel_btn.set_visible(False)
        self.progress.set_visible(False)

    def _run(self, *_):
        if not shutil.which("ffmpeg"):
            self._toast("ffmpeg no encontrado — sudo apt install ffmpeg")
            return
        self._cancel_requested = False
        self.progress.set_visible(True)
        self.progress.set_fraction(0)
        self.log_scroll.set_visible(True)
        self.run_btn.set_sensitive(False)
        self.cancel_btn.set_visible(True)
        self.log_buffer.set_text("")

        if self.batch_queue:
            out_dir = self.output_entry.get_text().strip()
            jobs = []
            for path in self.batch_queue:
                base = os.path.splitext(os.path.basename(path))[0]
                outp = (os.path.join(out_dir, base + "_converted")
                        if out_dir else
                        os.path.join(os.path.dirname(path), base + "_converted"))
                jobs.append((os.path.basename(path),
                             self._build_command(inp=path, outp=outp)))
            total = len(jobs)

            def worker():
                final_rc = 0
                for i, (name, cmd) in enumerate(jobs):
                    if self._cancel_requested:
                        GLib.idle_add(self._append_log, "\n── Lote interrumpido ──\n")
                        final_rc = -1
                        break
                    GLib.idle_add(self.progress.set_fraction, i / total)
                    GLib.idle_add(self._append_log, f"\n── [{i + 1}/{total}] {name} ──\n")
                    rc = self._exec(cmd)
                    if self._cancel_requested:
                        GLib.idle_add(self._append_log, f"⏹ Detenido: {name}\n")
                        final_rc = -1
                        break
                    GLib.idle_add(self._append_log,
                                  f"{'✓ OK' if rc == 0 else '✗ Error'}: {name}\n")
                    if rc != 0:
                        final_rc = rc
                if not self._cancel_requested:
                    GLib.idle_add(self.progress.set_fraction, 1.0)
                GLib.idle_add(self._finish, final_rc)
            threading.Thread(target=worker, daemon=True).start()
        else:
            start, end = self.cmd_buffer.get_bounds()
            cmd = self.cmd_buffer.get_text(start, end, False)
            if not cmd.strip():
                self._finish(0)
                return

            def worker():
                rc = self._exec(cmd)
                if self._cancel_requested:
                    rc = -1
                GLib.idle_add(self._finish, rc)
            threading.Thread(target=worker, daemon=True).start()
        GLib.timeout_add(200, self._pulse)

    def _exec(self, cmd):
        lines = []
        for line in cmd.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            lines.append(line)
        if not lines:
            return 0
        rc = 0
        for line in lines:
            if self._cancel_requested:
                return -1
            try:
                # stdout a DEVNULL evita deadlock (PIPE sin leer llena el buffer)
                proc = subprocess.Popen(
                    ["bash", "-c", line],
                    stderr=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    text=True,
                    preexec_fn=os.setsid,
                    bufsize=1)
                self.process = proc
                # Acumular stderr y volcar a la UI de a bloques (no por cada línea)
                buf = []
                for err_line in proc.stderr:
                    if self._cancel_requested:
                        self._kill_process()
                        break
                    buf.append(err_line)
                    if len(buf) >= 12:
                        chunk = "".join(buf)
                        buf.clear()
                        GLib.idle_add(self._append_log, chunk)
                if buf:
                    GLib.idle_add(self._append_log, "".join(buf))
                proc.wait()
                if self._cancel_requested:
                    return -1
                rc = proc.returncode
                if rc != 0:
                    break
            except Exception as ex:
                GLib.idle_add(self._append_log, f"Error: {ex}\n")
                rc = 1
                break
        self.process = None
        return rc

    def _pulse(self):
        if not self.run_btn.get_sensitive():
            self.progress.pulse()
            return True
        return False

    def _append_log(self, text):
        """Inserta en el log y recorta si crece demasiado (evita tilde de UI)."""
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text)
        # Limitar a ~4000 líneas
        line_count = self.log_buffer.get_line_count()
        if line_count > 4000:
            start = self.log_buffer.get_start_iter()
            cut = self.log_buffer.get_iter_at_line(line_count - 3000)
            self.log_buffer.delete(start, cut)
        self.log_view.scroll_to_iter(
            self.log_buffer.get_end_iter(), 0, False, 0, 0)

    def _finish(self, returncode):
        self.run_btn.set_sensitive(True)
        self.cancel_btn.set_visible(False)
        self.progress.set_visible(False)
        cancelled = self._cancel_requested or returncode == -1
        self._cancel_requested = False
        if cancelled:
            self._toast("⏹ Proceso terminado")
        elif returncode == 0:
            self.progress.set_fraction(1.0)
            self._toast("✓ Listo — podés usar «Limpiar» para otro archivo")
        else:
            self._toast("✗ Error — revisa el log")

    def _toast(self, msg):
        t = Adw.Toast.new(msg)
        t.set_timeout(4)
        self.toast.add_toast(t)

    def _show_about(self, *_):
        about = Adw.AboutWindow(transient_for=self)
        about.set_application_name("Argent Media Converter")
        about.set_application_icon(APP_ID)
        about.set_version(VERSION)
        about.set_developer_name("Tavo78ok")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_website("https://github.com/Tavo78ok/argent-media-converter")
        about.set_comments(
            "Conversor multimedia moderno para Linux.\n"
            "GTK4 + Libadwaita · NVENC / VAAPI / QSV · Lotes · Filtros.")
        about.set_developers(["Tavo78ok"])
        about.present()


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        # Forzar tema oscuro en toda la app (evita paneles blancos del sistema)
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception:
            pass
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        win = ConverterWindow(app)
        win.present()


def main():
    return Application().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
