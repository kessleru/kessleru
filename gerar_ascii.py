#!/usr/bin/env python3
"""
Converte uma foto em arte ASCII e salva em ascii_art.txt.

    pip install pillow numpy
    python gerar_ascii.py foto.jpg

Como funciona:
  1. Recorta o retrato e apaga o fundo com uma mascara (elipse na cabeca +
     trapezio nos ombros).
  2. Monta o tom de cada pixel combinando luminosidade com um "canal de pele"
     (R - B). So a luminosidade nao serve: nesta foto o cabelo e a pele tem
     quase o mesmo cinza, e o rosto sumia no meio do cabelo.
  3. Soma um passa-alta para realcar olhos, nariz e boca.
  4. Reduz para a grade de caracteres e mapeia cada celula na rampa NIVEIS,
     que esta ordenada pela densidade real de tinta de cada glifo.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# --------------------------------------------------------------- ajustes

RECORTE = (400, 470, 970, 1320)   # (esquerda, topo, direita, base) em pixels
LARGURA = 54                      # colunas de caractere; 48 a 64 funciona bem
PROPORCAO = 0.46                  # altura/largura do caractere na fonte

W_PELE = 0.65                     # peso do canal de pele contra o cabelo
K_DETALHE = 2.1                   # realce de olhos, nariz e boca
RAIO_DETALHE = 12
CORTE_BAIXO, CORTE_ALTO = 0.14, 0.95

# rampa ordenada pela densidade de tinta do glifo (escuro -> claro).
# a ordem importa: "@%#*+=-:. " parece certo mas nao e monotonica
# ('#' e mais denso que '%'), e isso suja a imagem inteira.
NIVEIS = "@#%=+*:-. "

# --------------------------------------------------------------- interno


def _blur(a, r):
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def _mascara(w, h, suavizar=30, desvanecer=0.14):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([0.09 * w, 0.01 * h, 0.91 * w, 0.80 * h], fill=255)          # cabeca
    d.polygon([(0.16 * w, h), (0.30 * w, 0.62 * h),
               (0.70 * w, 0.62 * h), (0.84 * w, h)], fill=255)             # ombros
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(suavizar))).astype(np.float32) / 255
    ys = np.linspace(0, 1, h)[:, None]
    inicio = 1 - desvanecer
    fade = np.clip(1 - (ys - inicio) / desvanecer, 0, 1)
    return m * np.where(ys > inicio, fade, 1.0)


def gerar(caminho):
    im = Image.open(caminho).convert("RGB").crop(RECORTE)
    w, h = im.size
    arr = np.asarray(im).astype(np.float32)
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]

    lum = (0.299 * R + 0.587 * G + 0.114 * B) / 255
    pele = np.clip((R - B - 12) / 48, 0, 1)

    # multiplicativo: mantem a pele clara e ainda deixa cabelo e camisa escuros
    base = (0.30 + 0.70 * lum) * ((1 - W_PELE) + W_PELE * pele)
    v = base + K_DETALHE * (lum - _blur(lum, RAIO_DETALHE))

    m = _mascara(w, h)
    v = np.clip(v, 0, 1) * m + 1.0 * (1 - m)

    dentro = v[m > 0.6]
    p2, p98 = np.percentile(dentro, 2), np.percentile(dentro, 98)
    v = np.clip((v - p2) / max(1e-6, p98 - p2), 0, 1)
    v = np.clip((v - CORTE_BAIXO) / (CORTE_ALTO - CORTE_BAIXO), 0, 1)

    img = Image.fromarray((v * 255).astype(np.uint8))
    altura = max(1, int(LARGURA * (img.height / img.width) * PROPORCAO))
    celulas = np.asarray(img.resize((LARGURA, altura), Image.LANCZOS)).astype(np.float32) / 255

    idx = (celulas * (len(NIVEIS) - 1)).round().astype(int)
    linhas = ["".join(NIVEIS[i] for i in linha).rstrip() for linha in idx]
    while linhas and not linhas[0].strip():
        linhas.pop(0)
    while linhas and not linhas[-1].strip():
        linhas.pop()
    return linhas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: python gerar_ascii.py foto.jpg")
    linhas = gerar(sys.argv[1])
    Path("ascii_art.txt").write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas))
    print(f"\nascii_art.txt: {len(linhas)} linhas x {max(len(l) for l in linhas)} colunas")
