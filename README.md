<img width="1440" height="900" alt="Captura de pantalla de 2026-09-23 01-12-19" src="https://github.com/user-attachments/assets/e04b8404-0d44-4c80-a5e8-669c8e4cd503" />
# Argent Media Converter

**Conversor multimedia moderno para Linux** · GTK4 + Libadwaita · FFmpeg

Convierte audio y vídeo con interfaz limpia, conversión por lotes, filtros y **encoders de hardware reales** (NVENC, VAAPI, QSV).

![Licencia](https://img.shields.io/badge/licencia-GPL--3.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-yellow)
![GTK](https://img.shields.io/badge/GTK-4-green)
![Plataforma](https://img.shields.io/badge/plataforma-Linux-orange)

---

<img width="1440" height="900" alt="Captura de pantalla de 2026-09-23 01-12-19" src="https://github.com/user-attachments/assets/52a68451-a54d-4fec-a922-0ef48a9139ad" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-23 01-12-32" src="https://github.com/user-attachments/assets/51cf994e-6d6f-4f59-9441-707093adfb1c" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-23 01-12-46" src="https://github.com/user-attachments/assets/6c75d7d4-915f-497a-bae4-62f2931ec998" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-23 01-12-59" src="https://github.com/user-attachments/assets/b8c87dfd-0771-4751-91f9-4bc072edcd78" />
<img width="1440" height="900" alt="Captura de pantalla de 2026-09-23 01-13-39" src="https://github.com/user-attachments/assets/66a0e697-1572-449a-98a3-98700edd3a37" />


## Características

| Área | Detalle |
|------|---------|
| **Audio** | MP3, AAC, M4A, FLAC, OGG, Opus, WAV, AIFF, WMA, AC3 |
| **Vídeo** | H.264 / H.265 (MP4, MKV, MOV), WebM VP8/VP9, GIF, AVI, 3GP |
| **Hardware** | NVIDIA NVENC · VAAPI (Intel/AMD) · Intel Quick Sync (QSV) — detección automática |
| **Filtros** | Volumen, loudnorm EBU R128, fade in/out, escala con aspecto preservado |
| **Lotes** | Varios archivos a la vez (Ctrl+clic en el selector) |
| **Extra** | Vista previa del comando FFmpeg, cancelar conversión, tema oscuro legible |

---

## Requisitos

```bash
# Debian / Ubuntu / Linux Mint
sudo apt update
sudo apt install python3 python3-gi python3-gi-cairo \
  gir1.2-gtk-4.0 gir1.2-adw-1 ffmpeg
```

**Drivers opcionales (aceleración por hardware):**

```bash
# VAAPI (Intel / AMD)
sudo apt install mesa-va-drivers
# Intel más reciente:
# sudo apt install intel-media-va-driver

# NVIDIA: drivers propietarios + libnvidia-encode-*
```

---

## Instalación

### Opción A — Paquete `.deb` (recomendado en Ubuntu/Debian)

```bash
sudo apt install ./argent-media-converter_2.1.4-1_all.deb
```

Después buscá **Argent Media Converter** en el menú de aplicaciones.

### Opción B — AppImage (portable)

```bash
chmod +x Argent_Media_Converter-2.1.4-x86_64.AppImage
./Argent_Media_Converter-2.1.4-x86_64.AppImage
```

Si en **Ubuntu 24.04+** no abre al hacer doble clic:

```bash
sudo apt install libfuse2t64
# o sin FUSE:
./Argent_Media_Converter-2.1.4-x86_64.AppImage --appimage-extract-and-run
```

> El AppImage usa Python, GTK y FFmpeg del sistema (no los embebe).  
> Si el `.deb` ya te funcionó, las dependencias ya están instaladas.

### Opción C — Desde el código fuente

```bash
git clone https://github.com/Tavo78ok/argent-media-converter.git
cd argent-media-converter
python3 argent_media_converter.py
```

---

## Uso rápido

1. **Elegir archivo…** (botón verde) — o varios con Ctrl+clic  
2. Elegí el **formato** en la barra izquierda (`.mp3`, `.mp4`, etc.)  
3. Arriba: modo **Audio** o **Vídeo**  
4. Ajustá calidad / tiempo si hace falta  
5. **▶ Convertir**

La salida se sugiere sola (`nombre_converted.ext`); podés cambiarla.

---

## Encoders de hardware

La app detecta qué backends tiene tu `ffmpeg` y solo muestra los disponibles.

| Backend | H.264 | H.265 | Calidad |
|---------|-------|-------|---------|
| **CPU** | `libx264` | `libx265` | `-crf` |
| **NVENC** (NVIDIA) | `h264_nvenc` | `hevc_nvenc` | `-cq` + preset p1–p7 |
| **VAAPI** (Intel/AMD) | `h264_vaapi` | `hevc_vaapi` | `-qp` |
| **QSV** (Intel) | `h264_qsv` | `hevc_qsv` | `-global_quality` |

Al redimensionar con HW se usan filtros nativos (`scale_cuda`, `scale_vaapi`, `scale_qsv`).

---

## Empaquetado (desarrolladores)

```bash
# Generar .deb
bash packaging/build-deb.sh
# → dist/argent-media-converter_*.deb

# Generar AppImage (requiere appimagetool)
bash packaging/build-appimage.sh
# → dist/Argent_Media_Converter-*.AppImage
```

Estructura del proyecto:

```
argent-media-converter/
├── argent_media_converter.py   # Aplicación principal
├── data/                       # .desktop + AppStream metainfo
├── icons/                      # Icono SVG
├── debian/                     # Metadatos del paquete Deb
├── packaging/
│   ├── build-deb.sh
│   └── build-appimage.sh
└── README.md
```

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| AppImage no abre | `chmod +x …` y `sudo apt install libfuse2t64` |
| “Namespace Gtk not available” | `sudo apt install gir1.2-gtk-4.0 gir1.2-adw-1 python3-gi` |
| ffmpeg no encontrado | `sudo apt install ffmpeg` |
| NVENC no aparece | Drivers NVIDIA + `ffmpeg` con soporte NVENC |
| VAAPI falla | Comprobar `/dev/dri/renderD*` y `mesa-va-drivers` |
| Panel de ajustes en blanco | Usar versión **≥ 2.1.2** (tema oscuro forzado) |

---

## Licencia

**GPL-3.0-or-later** · © Tavo78ok

Parte del ecosistema OpenArgentOS.

---

## Enlaces

- Issues: [github.com/Tavo78ok/argent-media-converter/issues](https://github.com/Tavo78ok/argent-media-converter/issues)
- Releases: subí el `.deb`, el AppImage y el código en cada versión etiquetada

---

Hecho con GTK4, Libadwaita y FFmpeg.
