"""Streamlit dashboard to visualize the simulated robot/map and a fleet of motos.

Run: streamlit run dashboard/app.py

Features:
- Loads latest map image from `output/maps` (falls back to blank canvas).
- Overlays simulated bike positions and statuses.
- Shows a status table and alerts.
- Simple controls: number of bikes, refresh interval, start/stop simulation.
"""
import os
import time
from typing import List
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src` package is importable when
# running `streamlit run dashboard/app.py` (Streamlit may set cwd to the
# dashboard folder). We insert the repo root (parent of this file's parent)
# at the front of sys.path.
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
import streamlit as st

from src.config import settings
from dashboard.simulator import Simulator


st.set_page_config(page_title="Pátio - Dashboard", layout="wide")


def find_latest_map(path: str) -> str | None:
    if not os.path.isdir(path):
        return None
    imgs = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not imgs:
        return None
    imgs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return imgs[0]


def load_map_image(path: str, w_px: int, h_px: int) -> Image.Image:
    if path and os.path.isfile(path):
        try:
            img = Image.open(path).convert('RGB')
            img = img.resize((w_px, h_px))
            return img
        except Exception:
            pass
    # fallback blank
    return Image.new('RGB', (w_px, h_px), (240, 240, 240, 255))


def detect_scanned_bbox(img: Image.Image, diff_thresh: int = 15, min_pixels: int = 50):
    """Detecta a bbox (em pixels) da área 'escaneada' na imagem.
    
    - Usa a mediana das bordas como cor de fundo.
    - Marca como escaneado pixels cuja diferença absoluta para o fundo > diff_thresh.
    - Retorna (left, top, right, bottom) em pixels ou None se nada encontrado.
    """
    gray = np.array(img.convert("L"))
    h, w = gray.shape

    # pega bordas (faixas) para estimar fundo: top, bottom, left, right (10 pixels)
    band = 10
    top = gray[:band, :].ravel()
    bottom = gray[-band:, :].ravel()
    left = gray[:, :band].ravel()
    right = gray[:, -band:].ravel()
    border_vals = np.concatenate([top, bottom, left, right])
    bg = int(np.median(border_vals))

    # máscara de pixels que diferem do fundo
    mask = np.abs(gray.astype(int) - bg) > diff_thresh

    # se muito pouco, retorna None
    if mask.sum() < min_pixels:
        return None

    ys, xs = np.where(mask)
    top_px, left_px = ys.min(), xs.min()
    bottom_px, right_px = ys.max(), xs.max()

    # margem opcional (2% da maior dimensão)
    margin = int(max(w, h) * 0.02)
    left_px = max(0, left_px - margin)
    top_px = max(0, top_px - margin)
    right_px = min(w - 1, right_px + margin)
    bottom_px = min(h - 1, bottom_px + margin)

    return (left_px, top_px, right_px, bottom_px)


def draw_grid_zones(image: Image.Image, bbox_px: tuple, grid_rows: int = 3, grid_cols: int = 3) -> Image.Image:
    """Desenha um grid de zonas sobre a área detectada da planta.
    
    Args:
        image: Imagem PIL
        bbox_px: (left, top, right, bottom) em pixels da área escaneada
        grid_rows: Número de linhas do grid
        grid_cols: Número de colunas do grid
    
    Returns:
        Imagem com grid desenhado
    """
    img = image.copy()
    draw = ImageDraw.Draw(img)
    left, top, right, bottom = bbox_px
    
    width = right - left
    height = bottom - top
    
    # Desenhar linhas verticais
    for i in range(1, grid_cols):
        x = left + (width * i // grid_cols)
        draw.line([(x, top), (x, bottom)], fill=(0, 255, 0, 180), width=2)
    
    # Desenhar linhas horizontais
    for i in range(1, grid_rows):
        y = top + (height * i // grid_rows)
        draw.line([(left, y), (right, y)], fill=(0, 255, 0, 180), width=2)
    
    # Desenhar borda externa do grid
    draw.rectangle([left, top, right, bottom], outline=(0, 255, 0, 255), width=3)
    
    # Numerar as zonas
    try:
        zone_num = 1
        for row in range(grid_rows):
            for col in range(grid_cols):
                zone_x = left + (width * col // grid_cols) + width // (grid_cols * 2)
                zone_y = top + (height * row // grid_rows) + height // (grid_rows * 2)
                draw.text((zone_x - 10, zone_y - 10), f"Z{zone_num}", 
                         fill=(0, 255, 0, 255), font=None)
                zone_num += 1
    except Exception:
        pass
    
    return img


def get_bike_zone(x_m: float, y_m: float, bbox_m: tuple, grid_rows: int = 3, grid_cols: int = 3) -> int:
    """Retorna o número da zona (1-based) onde a moto está.
    
    Args:
        x_m, y_m: Coordenadas da moto em metros
        bbox_m: (xmin, xmax, ymin, ymax) em metros
        grid_rows, grid_cols: Dimensões do grid
    
    Returns:
        Número da zona (1 a grid_rows*grid_cols) ou 0 se fora da área
    """
    if bbox_m is None:
        return 0
    
    xmin, xmax, ymin, ymax = bbox_m
    
    # Verificar se está dentro da bbox
    if not (xmin <= x_m <= xmax and ymin <= y_m <= ymax):
        return 0
    
    # Calcular posição no grid
    width = xmax - xmin
    height = ymax - ymin
    
    col = int((x_m - xmin) / width * grid_cols)
    row = int((y_m - ymin) / height * grid_rows)
    
    # Clamping para evitar índice fora do range
    col = min(col, grid_cols - 1)
    row = min(row, grid_rows - 1)
    
    zone = row * grid_cols + col + 1
    return zone


def draw_markers(image: Image.Image, states: List[dict], map_meters: float, settings_obj) -> Image.Image:
    img = image.copy()
    draw = ImageDraw.Draw(img)
    w_px = settings_obj.map_width_px
    h_px = settings_obj.map_height_px

    def meter_to_px(x_m, y_m):
        x_px = int((x_m / map_meters) * w_px)
        y_px = int((1 - (y_m / map_meters)) * h_px)  # invert y for display
        return x_px, y_px

    for s in states:
        x_px, y_px = meter_to_px(s['x_m'], s['y_m'])
        status = s['status']
        color = {
            'idle': (50, 150, 255, 220),
            'in_use': (50, 200, 50, 220),
            'stopped': (255, 180, 0, 220),
            'maintenance': (220, 50, 50, 220)
        }.get(status, (0, 0, 0, 220))

        # draw circle
        r = 8
        draw.ellipse((x_px - r, y_px - r, x_px + r, y_px + r), fill=color, outline=(0, 0, 0))
        # id label
        draw.text((x_px + r + 2, y_px - r), str(s['id']), fill=(0, 0, 0))

    return img


def make_status_table(states: List[dict], bbox_m: tuple = None, grid_rows: int = 3, grid_cols: int = 3) -> pd.DataFrame:
    df = pd.DataFrame(states)
    df = df.rename(columns={
        'id': 'ID',
        'x_m': 'X (m)',
        'y_m': 'Y (m)',
        'status': 'Status',
        'battery': 'Battery (%)',
        'last_update': 'LastUpdate'
    })
    if 'Battery (%)' in df.columns:
        df['Battery (%)'] = df['Battery (%)'].astype(int)
    
    # Adicionar coluna de zona
    if bbox_m is not None:
        df['Zone'] = df.apply(lambda row: get_bike_zone(row['X (m)'], row['Y (m)'], bbox_m, grid_rows, grid_cols), axis=1)
        df['Zone'] = df['Zone'].apply(lambda z: f"Z{z}" if z > 0 else "—")
        return df[['ID', 'Status', 'Battery (%)', 'Zone', 'X (m)', 'Y (m)']]
    
    return df[['ID', 'Status', 'Battery (%)', 'X (m)', 'Y (m)']]


def collect_alerts(states: List[dict]) -> List[str]:
    alerts = []
    for s in states:
        if s['battery'] < 20:
            alerts.append(f"Bike {s['id']} low battery ({s['battery']}%)")
        if s['status'] == 'maintenance':
            alerts.append(f"Bike {s['id']} in maintenance")
    return alerts


def main():
    st.sidebar.title("Controles")
    refresh_sec = st.sidebar.slider("Atualizar a cada (s)", min_value=1, max_value=10, value=2)
    n_bikes = st.sidebar.slider("Número de motos (simuladas)", 1, 30, 8)
    start = st.sidebar.button("Iniciar/Resetar sim")
    show_bbox = st.sidebar.checkbox("Mostrar bbox detectada", value=False)
    show_zones = st.sidebar.checkbox("Mostrar zonas (grid)", value=True)
    grid_rows = st.sidebar.slider("Zonas (linhas)", 2, 5, 3)
    grid_cols = st.sidebar.slider("Zonas (colunas)", 2, 5, 3)

    if 'sim' not in st.session_state or start:
        st.session_state.sim = Simulator(n_bikes, seed=int(time.time()) % 9999)
        st.session_state.last_step = time.time()

    # adjust bike count if changed
    if st.session_state.sim.n != n_bikes:
        st.session_state.sim.set_bike_count(n_bikes)

    # step simulator
    now = time.time()
    dt = now - st.session_state.get('last_step', now)
    dt = max(0.1, min(5.0, dt))
    st.session_state.sim.step(dt=dt)
    st.session_state.last_step = now

    # layout
    col1, col2 = st.columns((2, 1))

    # Map + markers
    with col1:
        st.header("Mapa do Pátio (gerado pelo SLAM)")
        latest = find_latest_map(settings.map_output_dir)
        img = load_map_image(latest, settings.map_width_px, settings.map_height_px)

        # Detecta a área escaneada (planta central) usando diferença do fundo
        detected = detect_scanned_bbox(img, diff_thresh=15, min_pixels=100)
        bbox_m = None
        
        if detected is not None:
            left_px, top_px, right_px, bottom_px = detected
            w_px = settings.map_width_px
            h_px = settings.map_height_px
            
            # converter pixels para metros
            x_min_m = (left_px / w_px) * settings.map_size_meters
            x_max_m = (right_px / w_px) * settings.map_size_meters
            # Y invertido: top_px (menor y) -> maior coordenada em metros
            y_min_m = (1 - (bottom_px / h_px)) * settings.map_size_meters
            y_max_m = (1 - (top_px / h_px)) * settings.map_size_meters
            bbox_m = (x_min_m, x_max_m, y_min_m, y_max_m)
            
            st.session_state.sim.set_allowed_bbox(bbox_m)
            
            # desenhar zonas se habilitado
            if show_zones:
                img = draw_grid_zones(img, detected, grid_rows, grid_cols)
            
            # desenhar bbox para debug se habilitado
            if show_bbox:
                img_debug = img.copy()
                draw_debug = ImageDraw.Draw(img_debug)
                draw_debug.rectangle([left_px, top_px, right_px, bottom_px], outline=(255, 0, 0), width=3)
                img = img_debug
        else:
            # fallback: sem restrição se nada detectado
            st.session_state.sim.set_allowed_bbox(None)

        # sobrepor marcadores das motos
        states = st.session_state.sim.get_states()
        img_with = draw_markers(img, states, settings.map_size_meters, settings)
        st.image(img_with, width='stretch')

    with col2:
        st.header("Status das motos")
        df = make_status_table(states, bbox_m, grid_rows, grid_cols)
        st.dataframe(df)

        st.markdown("### Alertas / Indicadores")
        alerts = collect_alerts(states)
        if alerts:
            for a in alerts:
                st.error(a)
        else:
            st.success("Nenhum alerta crítico")

        st.markdown("---")
        st.markdown("**Legenda**")
        st.markdown("- Verde: em uso | Amarelo: parado | Azul: idle | Vermelho: manutenção")
        
        # Mostrar contagem por zona se zonas estiverem habilitadas
        if show_zones and bbox_m is not None:
            st.markdown("### Motos por Zona")
            zone_counts = {}
            for s in states:
                z = get_bike_zone(s['x_m'], s['y_m'], bbox_m, grid_rows, grid_cols)
                if z > 0:
                    zone_counts[f"Z{z}"] = zone_counts.get(f"Z{z}", 0) + 1
            
            if zone_counts:
                for zone, count in sorted(zone_counts.items()):
                    st.text(f"{zone}: {count} moto(s)")
            else:
                st.text("Nenhuma moto nas zonas")

    # Auto-refresh usando sleep + rerun
    # Exibe um pequeno timer na sidebar
    st.sidebar.markdown("---")
    placeholder = st.sidebar.empty()
    placeholder.text(f"Atualizando em {refresh_sec}s...")
    time.sleep(refresh_sec)
    st.rerun()


if __name__ == '__main__':
    main()
